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
import boto3
# class UploadMedia():
#       UPLOAD_FOLDER = '/path/to/the/uploads'
#       ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'mp4', 'webp', 'mkv'}

#       @staticmethod
#       def allowed_file(filename):
#          return '.' in filename and \
#                filename.rsplit('.', 1)[1].lower() in UploadMedia.ALLOWED_EXTENSIONS


def upload_file_to_s3(file, bucket_name, acl="public-read"):
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
    return file.filename


class UploadImage(Resource):
    @f_jwt.jwt_required()
    def post(self):
        if "file" not in request.files:
            return "No user_file key in request.files"

        source_file = request.files["file"]

        if source_file.filename == "":
            return "Please select a file"

        if source_file:

            source_filename = secure_filename(source_file.filename)
            source_extension = os.path.splitext(source_filename)[1]
            destination_filename = uuid4().hex + source_extension
            app.logger.debug("destination file name= %s", destination_filename)
            source_file.filename = destination_filename
            path_name = upload_file_to_s3(
                source_file, app.config["S3_BUCKET"])
            # return str(output)
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
                "path": path_name,
                "full_url": full_url
            }
            return media_dict, 201
        else:
            abort(404)


class UploadVideo(Resource):
    pass


class UploadFile(Resource):
    pass
