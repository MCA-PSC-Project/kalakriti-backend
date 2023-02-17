from datetime import datetime
import os
from uuid import uuid4
from flask import abort, request
import flask_jwt_extended as f_jwt
from flask import current_app as app
from flask_restful import Resource
import psycopg2
from werkzeug.utils import secure_filename
import app.main as main


def upload_file_to_bucket(file, bucket_name, acl="public-read"):
    """
    Docs: http://boto3.readthedocs.io/en/latest/guide/s3.html
    """
    try:
        main.s3.upload_fileobj(
            file,
            bucket_name,
            file.filename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type  # Set appropriate content type as per the file
            }
        )
    except Exception as e:
        print("Something Happened: ", e)
        app.logger.debug(e)
        return False
    return file.filename


def delete_file_from_bucket(file_path, bucket_name):
    try:
        response = main.s3.delete_object(Bucket=bucket_name, Key=file_path)
    except Exception as e:
        print("Something Happened: ", e)
        app.logger.debug(e)
        return False
    return True


def delete_media_by_id(media_id):
    GET_MEDIA_PATH = 'SELECT path FROM media WHERE id= %s'
    # catch exception for invalid SQL statement
    try:
        # declare a cursor object from the connection
        cursor = main.db_conn.cursor()
        # app.logger.debug("cursor object: %s", cursor)

        cursor.execute(GET_MEDIA_PATH, (media_id,))
        row = cursor.fetchone()
        if row is None:
            abort(400, 'Bad Request')
        file_path = row[0]
    except (Exception, psycopg2.Error) as err:
        app.logger.debug(err)
        return False
    finally:
        cursor.close()

    result = delete_file_from_bucket(file_path, app.config['S3_BUCKET'])
    if result is False:
        return False
    else:
        DELETE_MEDIA = 'DELETE FROM media WHERE id= %s'
        try:
            cursor = main.db_conn.cursor()
            cursor.execute(DELETE_MEDIA, (media_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            return False
        finally:
            cursor.close()
    return True


class DeleteMedia(Resource):
    @f_jwt.jwt_required()
    def delete(self, media_id):
        if delete_media_by_id(media_id):
            return 200
        else:
            return 400


class UploadImage(Resource):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    @f_jwt.jwt_required()
    def post(self):
        if "file" not in request.files:
            return "No user_file key in request.files", 400

        source_file = request.files["file"]

        if source_file.filename == "":
            return "Please select a file", 400

        if source_file:
            ext = source_file.filename.rsplit('.', 1)[1].lower()
            if ext not in UploadImage.ALLOWED_EXTENSIONS:
                return "File type not allowed", 400

            source_filename = secure_filename(source_file.filename)
            source_extension = os.path.splitext(source_filename)[1]
            destination_filename = uuid4().hex + source_extension
            app.logger.debug("destination file name= %s", destination_filename)
            source_file.filename = destination_filename
            path_name = upload_file_to_bucket(
                source_file, app.config["S3_BUCKET"])
            if path_name is False:
                return "Error in uploading to s3 bucket", 400
            full_url = "{}/{}".format(app.config["S3_LOCATION"], path_name)
            app.logger.debug(str(full_url))

            current_time = datetime.now()
            INSERT_MEDIA = '''INSERT INTO media(name, path, media_type, added_at)
         VALUES(%s, %s, %s, %s) RETURNING id'''

            # catch exception for invalid SQL statement
            try:
                # declare a cursor object from the connection
                cursor = main.db_conn.cursor()
                # app.logger.debug("cursor object: %s", cursor)

                cursor.execute(INSERT_MEDIA, (source_filename,
                               path_name, 'image', current_time,))
                media_id = cursor.fetchone()[0]
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, 'Bad Request')
            finally:
                cursor.close()
            media_dict = {
                "id": media_id,
                "media_type": 'image',
                "media_name": source_filename,
                "path": path_name,
                "full_url": full_url
            }
            return media_dict, 201
        else:
            abort(404)


class UploadAudio(Resource):
    ALLOWED_EXTENSIONS = {'mp3', 'ogg'}

    @f_jwt.jwt_required()
    def post(self):
        if "file" not in request.files:
            return "No user_file key in request.files", 400

        source_file = request.files["file"]

        if source_file.filename == "":
            return "Please select a file", 400

        if source_file:
            ext = source_file.filename.rsplit('.', 1)[1].lower()
            if ext not in UploadAudio.ALLOWED_EXTENSIONS:
                return "File type not allowed", 400

            source_filename = secure_filename(source_file.filename)
            source_extension = os.path.splitext(source_filename)[1]
            destination_filename = uuid4().hex + source_extension
            app.logger.debug("destination file name= %s", destination_filename)
            source_file.filename = destination_filename
            path_name = upload_file_to_bucket(
                source_file, app.config["S3_BUCKET"])
            if path_name is False:
                return "Error in uploading to s3 bucket", 400
            full_url = "{}/{}".format(app.config["S3_LOCATION"], path_name)
            app.logger.debug(str(full_url))

            current_time = datetime.now()
            INSERT_MEDIA = '''INSERT INTO media(name, path, media_type, added_at)
         VALUES(%s, %s, %s, %s) RETURNING id'''

            # catch exception for invalid SQL statement
            try:
                # declare a cursor object from the connection
                cursor = main.db_conn.cursor()
                # app.logger.debug("cursor object: %s", cursor)

                cursor.execute(INSERT_MEDIA, (source_filename,
                               path_name, 'audio', current_time,))
                media_id = cursor.fetchone()[0]
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, 'Bad Request')
            finally:
                cursor.close()
            media_dict = {
                "id": media_id,
                "media_type": 'audio',
                "media_name": source_filename,
                "path": path_name,
                "full_url": full_url
            }
            return media_dict, 201
        else:
            abort(404)


class UploadVideo(Resource):
    ALLOWED_EXTENSIONS = {'mp4', 'mkv'}

    @f_jwt.jwt_required()
    def post(self):
        if "file" not in request.files:
            return "No user_file key in request.files", 400

        source_file = request.files["file"]

        if source_file.filename == "":
            return "Please select a file", 400

        if source_file:
            ext = source_file.filename.rsplit('.', 1)[1].lower()
            if ext not in UploadVideo.ALLOWED_EXTENSIONS:
                return "File type not allowed", 400

            source_filename = secure_filename(source_file.filename)
            source_extension = os.path.splitext(source_filename)[1]
            destination_filename = uuid4().hex + source_extension
            app.logger.debug("destination file name= %s", destination_filename)
            source_file.filename = destination_filename
            path_name = upload_file_to_bucket(
                source_file, app.config["S3_BUCKET"])
            if path_name is False:
                return "Error in uploading to s3 bucket", 400
            full_url = "{}/{}".format(app.config["S3_LOCATION"], path_name)
            app.logger.debug(str(full_url))

            current_time = datetime.now()
            INSERT_MEDIA = '''INSERT INTO media(name, path, media_type, added_at)
         VALUES(%s, %s, %s, %s) RETURNING id'''

            # catch exception for invalid SQL statement
            try:
                # declare a cursor object from the connection
                cursor = main.db_conn.cursor()
                # app.logger.debug("cursor object: %s", cursor)

                cursor.execute(INSERT_MEDIA, (source_filename,
                               path_name, 'video', current_time,))
                media_id = cursor.fetchone()[0]
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, 'Bad Request')
            finally:
                cursor.close()
            media_dict = {
                "id": media_id,
                "media_type": 'video',
                "media_name": source_filename,
                "path": path_name,
                "full_url": full_url
            }
            return media_dict, 201
        else:
            abort(404)


class UploadFile(Resource):
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc',
                          'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

    @f_jwt.jwt_required()
    def post(self):
        if "file" not in request.files:
            return "No user_file key in request.files", 400

        source_file = request.files["file"]

        if source_file.filename == "":
            return "Please select a file", 400

        if source_file:
            ext = source_file.filename.rsplit('.', 1)[1].lower()
            if ext not in UploadFile.ALLOWED_EXTENSIONS:
                return "File type not allowed", 400

            source_filename = secure_filename(source_file.filename)
            source_extension = os.path.splitext(source_filename)[1]
            destination_filename = uuid4().hex + source_extension
            app.logger.debug("destination file name= %s", destination_filename)
            source_file.filename = destination_filename
            path_name = upload_file_to_bucket(
                source_file, app.config["S3_BUCKET"])
            if path_name is False:
                return "Error in uploading to s3 bucket", 400
            full_url = "{}/{}".format(app.config["S3_LOCATION"], path_name)
            app.logger.debug(str(full_url))

            current_time = datetime.now()
            INSERT_MEDIA = '''INSERT INTO media(name, path, media_type, added_at)
         VALUES(%s, %s, %s, %s) RETURNING id'''

            # catch exception for invalid SQL statement
            try:
                # declare a cursor object from the connection
                cursor = main.db_conn.cursor()
                # app.logger.debug("cursor object: %s", cursor)

                cursor.execute(INSERT_MEDIA, (source_filename,
                               path_name, 'file', current_time,))
                media_id = cursor.fetchone()[0]
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, 'Bad Request')
            finally:
                cursor.close()
            media_dict = {
                "id": media_id,
                "media_type": 'file',
                "media_name": source_filename,
                "path": path_name,
                "full_url": full_url
            }
            return media_dict, 201
        else:
            abort(404)
