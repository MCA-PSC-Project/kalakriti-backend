from datetime import datetime
import bcrypt
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.main as main
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class UserProfile(Resource):
    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        # user_id=20
        app.logger.debug("user_id= %s", user_id)
        user_profile_dict = {}

        GET_PROFILE = '''SELECT name, email, phone, TO_CHAR(dob, 'YYYY-MM-DD'), gender FROM users WHERE id= %s'''
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_PROFILE, (user_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                user_profile_dict['name'] = row[0]
                user_profile_dict['email'] = row[1]
                user_profile_dict['phone'] = row[2]
                user_profile_dict['dob'] = row[3]
                user_profile_dict['gender'] = row[4]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        app.logger.debug(user_profile_dict)
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
        UPDATE_USER = 'UPDATE users SET name= %s, dob=%s, gender=%s, updated_at= %s WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_USER, (user_dict['name'], user_dict['dob'], user_dict['gender'], current_time, user_id,))
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"user {user_dict['name']} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self):
        user_id = f_jwt.get_jwt_identity()
        # user_id=20
        app.logger.debug("user_id=%s", user_id)

        DELETE_USER = 'DELETE FROM users WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            app.logger.debug("cursor object: %s", cursor, "\n")

            cursor.execute(DELETE_USER, (user_id,))
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
            cursor = main.db_conn.cursor()
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
            cursor = main.db_conn.cursor()
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
            cursor = main.db_conn.cursor()
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
