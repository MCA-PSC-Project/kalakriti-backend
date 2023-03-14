from datetime import datetime
import bcrypt
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
from flask import current_app as app

class ResetEmail(Resource):
    @f_jwt.jwt_required()
    def patch(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        data = request.get_json()
        email = data.get('email', None)
        app.logger.debug(email)
        if not email:
            abort(400, 'Bad Request')
        current_time = datetime.now()
        # app.logger.debug("cur time : %s", current_time)

        UPDATE_USER_EMAIL = 'UPDATE users SET email= %s, updated_at= %s WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(UPDATE_USER_EMAIL, (email, current_time, user_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"user with id {user_id}, email modified."}, 200


class ResetMobile(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        provided_mobile_no = data.get('mobile_no', None)
        provided_motp = data.get("motp", None)

        if not provided_mobile_no or not provided_motp:
            app.logger.debug("Both mobile_no and motp must be provided")
            abort(400, 'Bad Request')

        GET_MOTP_AND_EXPIRY = '''SELECT motp, expiry_at FROM mobile_otp WHERE mobile_no= %s'''
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_MOTP_AND_EXPIRY, (provided_mobile_no,))
            row = cursor.fetchone()
            if row is None:
                app.logger.debug("No such mobile no in mobile_otp table")
                abort(400, 'Bad Request')
            stored_motp = row.motp
            expiry_at = row.expiry_at
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        if provided_motp != stored_motp or datetime.now(expiry_at.tzinfo) > expiry_at:
            abort(400, 'Bad Request')

        if user_type == 'super_admin':
            user_type = 'admin'
        table_name = user_type+'s'
        UPDATE_MOBILE_NUMBER = '''UPDATE {} SET mobile_no= %s, updated_at= %s WHERE id= %s'''.format(table_name)
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(UPDATE_MOBILE_NUMBER,
                           (provided_mobile_no, datetime.now(), user_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"mobile_no updated successfully."}, 200


class ResetPassword(Resource):
    def post(self):
        data = request.get_json()
        email = data.get("email", None)
        new_password = data.get("new_password", None)

        if not email or not new_password:
            abort(400, 'Bad Request')
        current_time = datetime.now()
        # app.logger.debug("cur time : %s", current_time)

        new_hashed_password = bcrypt.hashpw(
            new_password.encode('utf-8'), bcrypt.gensalt())
        new_hashed_password = new_hashed_password.decode('utf-8')

        CHANGE_USER_PASSWORD = 'UPDATE users SET password= %s, updated_at= %s WHERE email= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(CHANGE_USER_PASSWORD,
                           (new_hashed_password, current_time, email,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": "Status accepted"}, 202
