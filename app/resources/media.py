from datetime import datetime, timezone
import os
from uuid import uuid4
from flask import abort, request
import flask_jwt_extended as f_jwt
from flask import current_app as app
from flask_restful import Resource
import psycopg2
from werkzeug.utils import secure_filename
import app.app_globals as app_globals
import filetype


def upload_file_to_bucket(file, bucket_name, acl="public-read"):
    """
    Docs: http://boto3.readthedocs.io/en/latest/guide/s3.html
    """
    try:
        app_globals.s3.upload_fileobj(
            file,
            bucket_name,
            file.filename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type,  # Set appropriate content type as per the file
            },
        )
    except Exception as e:
        print("Something Happened: ", e)
        app.logger.debug(e)
        return False
    return file.filename


def delete_file_from_bucket(file_path, bucket_name):
    try:
        response = app_globals.s3.delete_object(Bucket=bucket_name, Key=file_path)
    except Exception as e:
        print("Something Happened: ", e)
        app.logger.debug(e)
        return False
    return True


def delete_media_by_id(media_id):
    GET_MEDIA_PATH = "SELECT path FROM media WHERE id= %s"
    # catch exception for invalid SQL statement
    try:
        # declare a cursor object from the connection
        cursor = app_globals.get_cursor()
        # app.logger.debug("cursor object: %s", cursor)
        cursor.execute(GET_MEDIA_PATH, (media_id,))
        row = cursor.fetchone()
        if row is None:
            abort(400, "Bad Request")
        file_path = row[0]
    except (Exception, psycopg2.Error) as err:
        app.logger.debug(err)
        return False
    finally:
        cursor.close()

    result = delete_file_from_bucket(file_path, app.config["S3_BUCKET"])
    if result is False:
        return False
    else:
        DELETE_MEDIA = "DELETE FROM media WHERE id= %s"
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(DELETE_MEDIA, (media_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, "Bad Request: delete row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            return False
        finally:
            cursor.close()
    return True


def delete_medias_by_ids(media_ids):
    path_list = []
    GET_MEDIAS_PATH = """SELECT path FROM media WHERE id IN %s"""
    try:
        cursor = app_globals.get_cursor()
        cursor.execute(GET_MEDIAS_PATH, (media_ids,))
        rows = cursor.fetchall()
        if not rows:
            abort(400, "Bad Request")
        for row in rows:
            path = {"Key": row[0]}
            path_list.append(path)
        app.logger.debug("paths= %s", path_list)
    except (Exception, psycopg2.Error) as err:
        app.logger.debug(err)
        return False
    finally:
        cursor.close()

    bucket_name = app.config["S3_BUCKET"]
    files_to_delete = path_list
    result = app_globals.s3.delete_objects(
        Bucket=bucket_name, Delete={"Objects": files_to_delete}
    )
    # app.logger.debug(result)
    if result is False:
        return False
    else:
        DELETE_MEDIA = "DELETE FROM media WHERE id IN %s"
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(DELETE_MEDIA, (media_ids,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount == 0:
                abort(400, "Bad Request: delete media rows error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            return False
        finally:
            cursor.close()
    return result


class DeleteMedia(Resource):
    @f_jwt.jwt_required()
    def delete(self, media_id):
        if delete_media_by_id(media_id):
            return 200
        else:
            return 400


class UploadImage(Resource):
    ALLOWED_IMAGE_MIME_TYPES = [
        "image/bmp",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/svg+xml",
        "image/tiff",
        "image/webp",
    ]

    @f_jwt.jwt_required()
    def post(self):
        if "file" not in request.files:
            return "No file key in request.files", 400

        source_file = request.files["file"]

        if source_file.filename == "":
            return "Please select a file", 400

        if source_file:
            kind = filetype.guess(source_file)
            if kind is None:
                print("Cannot guess file type!")
            else:
                print(f"File MIME type: {kind.mime}")
                print(f"File extension: {kind.extension}")

            # ext = source_file.filename.rsplit(".", 1)[1].lower()
            if kind.mime not in UploadImage.ALLOWED_IMAGE_MIME_TYPES:
                return "File type not allowed", 400

            source_filename = secure_filename(source_file.filename)
            # source_extension = os.path.splitext(source_filename)[1]
            source_extension = "." + kind.extension
            destination_filename = uuid4().hex + source_extension
            app.logger.debug("destination file name= %s", destination_filename)
            source_file.filename = destination_filename
            path_name = upload_file_to_bucket(source_file, app.config["S3_BUCKET"])
            if path_name is False:
                return "Error in uploading to s3 bucket", 400
            full_url = "{}/{}".format(app.config["S3_LOCATION"], path_name)
            app.logger.debug(str(full_url))

            current_time = datetime.now(timezone.utc)
            INSERT_MEDIA = """INSERT INTO media(name, path, media_type, added_at)
         VALUES(%s, %s, %s, %s) RETURNING id"""

            # catch exception for invalid SQL statement
            try:
                # declare a cursor object from the connection
                cursor = app_globals.get_cursor()
                # # app.logger.debug("cursor object: %s", cursor)

                cursor.execute(
                    INSERT_MEDIA,
                    (
                        source_filename,
                        path_name,
                        "image",
                        current_time,
                    ),
                )
                media_id = cursor.fetchone()[0]
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, "Bad Request")
            finally:
                cursor.close()
            media_dict = {
                "id": media_id,
                "media_type": "image",
                "media_name": source_filename,
                "path": path_name,
                "full_url": full_url,
            }
            return media_dict, 201
        else:
            abort(404)


class UploadAudio(Resource):
    ALLOWED_AUDIO_MIME_TYPES = [
        "audio/aac",
        "audio/midi",
        "audio/x-midi",
        "audio/mpeg",
        "audio/ogg",
        "audio/opus",
        "audio/wav",
        "audio/webm",
        "audio/3gpp",
        "audio/3gpp2",
    ]

    @f_jwt.jwt_required()
    def post(self):
        if "file" not in request.files:
            return "No file key in request.files", 400

        source_file = request.files["file"]

        if source_file.filename == "":
            return "Please select a file", 400

        if source_file:
            kind = filetype.guess(source_file)
            if kind is None:
                print("Cannot guess file type!")
            else:
                print(f"File MIME type: {kind.mime}")
                print(f"File extension: {kind.extension}")
            # ext = source_file.filename.rsplit(".", 1)[1].lower()
            if kind.mime not in UploadAudio.ALLOWED_AUDIO_MIME_TYPES:
                return "File type not allowed", 400

            source_filename = secure_filename(source_file.filename)
            # source_extension = os.path.splitext(source_filename)[1]
            source_extension = "." + kind.extension
            destination_filename = uuid4().hex + source_extension
            app.logger.debug("destination file name= %s", destination_filename)
            source_file.filename = destination_filename
            path_name = upload_file_to_bucket(source_file, app.config["S3_BUCKET"])
            if path_name is False:
                return "Error in uploading to s3 bucket", 400
            full_url = "{}/{}".format(app.config["S3_LOCATION"], path_name)
            app.logger.debug(str(full_url))

            current_time = datetime.now(timezone.utc)
            INSERT_MEDIA = """INSERT INTO media(name, path, media_type, added_at)
         VALUES(%s, %s, %s, %s) RETURNING id"""

            # catch exception for invalid SQL statement
            try:
                # declare a cursor object from the connection
                cursor = app_globals.get_cursor()
                # # app.logger.debug("cursor object: %s", cursor)

                cursor.execute(
                    INSERT_MEDIA,
                    (
                        source_filename,
                        path_name,
                        "audio",
                        current_time,
                    ),
                )
                media_id = cursor.fetchone()[0]
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, "Bad Request")
            finally:
                cursor.close()
            media_dict = {
                "id": media_id,
                "media_type": "audio",
                "media_name": source_filename,
                "path": path_name,
                "full_url": full_url,
            }
            return media_dict, 201
        else:
            abort(404)


class UploadVideo(Resource):
    ALLOWED_VIDEO_MIME_TYPES = [
        "video/x-msvideo",
        "video/mp4",
        "video/mpeg",
        "video/ogg",
        "video/webm",
        "video/3gpp",
        "video/3gpp2",
    ]

    @f_jwt.jwt_required()
    def post(self):
        if "file" not in request.files:
            return "No file key in request.files", 400

        source_file = request.files["file"]

        if source_file.filename == "":
            return "Please select a file", 400

        if source_file:
            kind = filetype.guess(source_file)
            if kind is None:
                print("Cannot guess file type!")
            else:
                print(f"File MIME type: {kind.mime}")
                print(f"File extension: {kind.extension}")
            # ext = source_file.filename.rsplit(".", 1)[1].lower()
            if kind.mime not in UploadVideo.ALLOWED_VIDEO_MIME_TYPES:
                return "File type not allowed", 400

            source_filename = secure_filename(source_file.filename)
            # source_extension = os.path.splitext(source_filename)[1]
            source_extension = "." + kind.extension
            destination_filename = uuid4().hex + source_extension
            app.logger.debug("destination file name= %s", destination_filename)
            source_file.filename = destination_filename
            path_name = upload_file_to_bucket(source_file, app.config["S3_BUCKET"])
            if path_name is False:
                return "Error in uploading to s3 bucket", 400
            full_url = "{}/{}".format(app.config["S3_LOCATION"], path_name)
            app.logger.debug(str(full_url))

            current_time = datetime.now(timezone.utc)
            INSERT_MEDIA = """INSERT INTO media(name, path, media_type, added_at)
         VALUES(%s, %s, %s, %s) RETURNING id"""

            # catch exception for invalid SQL statement
            try:
                # declare a cursor object from the connection
                cursor = app_globals.get_cursor()
                # # app.logger.debug("cursor object: %s", cursor)

                cursor.execute(
                    INSERT_MEDIA,
                    (
                        source_filename,
                        path_name,
                        "video",
                        current_time,
                    ),
                )
                media_id = cursor.fetchone()[0]
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, "Bad Request")
            finally:
                cursor.close()
            media_dict = {
                "id": media_id,
                "media_type": "video",
                "media_name": source_filename,
                "path": path_name,
                "full_url": full_url,
            }
            return media_dict, 201
        else:
            abort(404)


class UploadFile(Resource):
    ALLOWED_FILE_MIME_TYPES = [
        "application/pdf",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/csv",
        "text/html",
    ]

    @f_jwt.jwt_required()
    def post(self):
        if "file" not in request.files:
            return "No file key in request.files", 400

        source_file = request.files["file"]

        if source_file.filename == "":
            return "Please select a file", 400

        if source_file:
            kind = filetype.guess(source_file)
            if kind is None:
                print("Cannot guess file type!")
            else:
                print(f"File MIME type: {kind.mime}")
                print(f"File extension: {kind.extension}")
            # ext = source_file.filename.rsplit(".", 1)[1].lower()
            if kind.mime not in UploadFile.ALLOWED_FILE_MIME_TYPES:
                return "File type not allowed", 400

            source_filename = secure_filename(source_file.filename)
            # source_extension = os.path.splitext(source_filename)[1]
            source_extension = "." + kind.extension
            destination_filename = uuid4().hex + source_extension
            app.logger.debug("destination file name= %s", destination_filename)
            source_file.filename = destination_filename
            path_name = upload_file_to_bucket(source_file, app.config["S3_BUCKET"])
            if path_name is False:
                return "Error in uploading to s3 bucket", 400
            full_url = "{}/{}".format(app.config["S3_LOCATION"], path_name)
            app.logger.debug(str(full_url))

            current_time = datetime.now(timezone.utc)
            INSERT_MEDIA = """INSERT INTO media(name, path, media_type, added_at)
         VALUES(%s, %s, %s, %s) RETURNING id"""

            # catch exception for invalid SQL statement
            try:
                # declare a cursor object from the connection
                cursor = app_globals.get_cursor()
                # # app.logger.debug("cursor object: %s", cursor)

                cursor.execute(
                    INSERT_MEDIA,
                    (
                        source_filename,
                        path_name,
                        "file",
                        current_time,
                    ),
                )
                media_id = cursor.fetchone()[0]
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, "Bad Request")
            finally:
                cursor.close()
            media_dict = {
                "id": media_id,
                "media_type": "file",
                "media_name": source_filename,
                "path": path_name,
                "full_url": full_url,
            }
            return media_dict, 201
        else:
            abort(404)


class BucketObjects(Resource):
    @f_jwt.jwt_required()
    def get(self):
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, "Forbidden: only super-admins and admins can view all sellers")

        bucket_name = app.config["S3_BUCKET"]
        objects = app_globals.s3.list_objects_v2(Bucket=bucket_name)
        object_details = []
        try:
            for object in objects.get("Contents"):
                object_details.append(
                    {"file_name": object.get("Key"), "size": object.get("Size")}
                )
        except Exception as err:
            app.logger.debug(err)
        return object_details

    @f_jwt.jwt_required()
    def delete(self):
        """
        This function deletes all files from S3 bucket
        """
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, "Forbidden: only super-admins and admins can view all sellers")

        bucket_name = app.config["S3_BUCKET"]
        # First we list all files
        response = app_globals.s3.list_objects_v2(Bucket=bucket_name)
        files = response.get("Contents")
        files_to_delete = []
        # We will create Key array to pass to delete_objects function
        for file in files:
            files_to_delete.append({"Key": file.get("Key")})
        response = app_globals.s3.delete_objects(
            Bucket=bucket_name, Delete={"Objects": files_to_delete}
        )
        app.logger.debug(response)
        return response
