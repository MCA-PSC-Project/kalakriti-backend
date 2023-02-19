from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class GetAllAdmins(Resource):
    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if user_type != "super_admin":
            abort(400, "only super_admin can see all admins")

        admin_list = []

        GET_ADMINS_PROFILES = '''SELECT first_name, last_name, user_type, email, phone, TO_CHAR(dob, 'YYYY-MM-DD'), gender, enabled
        FROM users WHERE user_type= %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_ADMINS_PROFILES, ('admin',))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                admin_profile_dict = {}
                admin_profile_dict['first_name'] = row[0]
                admin_profile_dict['last_name'] = row[1]
                admin_profile_dict['user_type'] = row[2]
                admin_profile_dict['email'] = row[3]
                admin_profile_dict['phone'] = row[4]
                admin_profile_dict['dob'] = row[5]
                admin_profile_dict['gender'] = row[6]
                admin_profile_dict['enabled'] = row[7]
                admin_list.append(admin_profile_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(admin_list)
        return admin_list


class PromoteToAdmin(Resource):
    @f_jwt.jwt_required()
    def put(self):
        # user_id = f_jwt.get_jwt_identity()
        # app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        email = data.get("email", None)

        if user_type != "super_admin":
            abort(400, "only super_admins have privilege to promote to admin")

        current_time = datetime.now()

        UPDATE_USER_ENABLED_STATUS = '''UPDATE users SET user_type= %s, updated_at= %s where email = %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(UPDATE_USER_ENABLED_STATUS, ('admin', current_time, email,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        return {"message": f"{email} is now admin"}, 200
