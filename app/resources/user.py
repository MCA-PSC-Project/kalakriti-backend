from datetime import datetime
import bcrypt
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class UserProfile(Resource):
    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        user_profile_dict = {}

        GET_PROFILE = '''SELECT u.first_name, u.last_name, u.user_type, u.email, u.phone, 
        TO_CHAR(u.dob, 'YYYY-MM-DD'), u.gender , u.enabled,
        m.id, m.name, m.path
        FROM users u LEFT JOIN media m on u.dp_id = m.id 
        WHERE u.id= %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_PROFILE, (user_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            user_profile_dict['first_name'] = row[0]
            user_profile_dict['last_name'] = row[1]
            user_profile_dict['user_type'] = row[2]
            user_profile_dict['email'] = row[3]
            user_profile_dict['phone'] = row[4]
            user_profile_dict['dob'] = row[5]
            user_profile_dict['gender'] = row[6]
            user_profile_dict['enabled'] = row[7]

            dp_media_dict = {}
            dp_media_dict['id'] = row[8]
            dp_media_dict['name'] = row[9]
            # media_dict['path'] = row[10]
            path = row[10]
            if path is not None:
                dp_media_dict['path'] = "{}/{}".format(
                    app.config["S3_LOCATION"], row[10])
            else:
                dp_media_dict['path'] = None
            user_profile_dict.update({"dp": dp_media_dict})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(user_profile_dict)
        return user_profile_dict

    @f_jwt.jwt_required()
    def put(self):
        user_id = f_jwt.get_jwt_identity()
        # user_id=20
        app.logger.debug("user_id= %s", user_id)
        data = request.get_json()
        user_dict = json.loads(json.dumps(data))
        app.logger.debug(user_dict)

        current_time = datetime.now()
        # app.logger.debug("cur time : %s", current_time)
        UPDATE_USER = 'UPDATE users SET first_name= %s, last_name= %s, dob=%s, gender=%s, updated_at= %s WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_USER, (user_dict['first_name'], user_dict['last_name'], user_dict['dob'],
                              user_dict['gender'], current_time, user_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"user_id {user_id} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self):
        user_id = f_jwt.get_jwt_identity()
        # user_id=20
        app.logger.debug("user_id=%s", user_id)

        DELETE_USER = 'DELETE FROM users WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            app.logger.debug("cursor object: %s", cursor, "\n")

            cursor.execute(DELETE_USER, (user_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200


class ResetEmail(Resource):
    @f_jwt.jwt_required()
    def patch(self):
        user_id = f_jwt.get_jwt_identity()
        # user_id=20
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
            # app.logger.debug("cursor object: %s", cursor)

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


class ResetPhone(Resource):
    @f_jwt.jwt_required()
    def patch(self):
        user_id = f_jwt.get_jwt_identity()
        # user_id=20
        app.logger.debug("user_id= %s", user_id)
        data = request.get_json()
        phone = data.get('phone', None)
        app.logger.debug(phone)
        if not phone:
            abort(400, 'Bad Request')
        current_time = datetime.now()
        # app.logger.debug("cur time : %s", current_time)

        UPDATE_USER_PHONE = 'UPDATE users SET phone= %s, updated_at= %s WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(UPDATE_USER_PHONE, (phone, current_time, user_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"user with id {user_id}, phone modified."}, 200


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
            # app.logger.debug("cursor object: %s", cursor)

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
