import os
from uuid import uuid4
from flask import abort, request
import flask_jwt_extended as f_jwt
from flask import current_app as app
from flask_restful import Resource
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
        return e
    return "{}/{}".format(app.config["S3_LOCATION"], file.filename)


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
            output = upload_file_to_s3(
                source_file, app.config["S3_BUCKET"])
            return str(output)
        else:
            abort(404)


class UploadVideo(Resource):
    pass


class UploadFile(Resource):
    pass
