from datetime import datetime
import bcrypt
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class CustomerProfile(Resource):
    @f_jwt.jwt_required()
    def get(self):
        customer_id = f_jwt.get_jwt_identity().get("customer_id")
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if (not customer_id) and (user_type != 'customer'):
            abort(403, 'Forbidden')

        customer_profile_dict = {}

        GET_CUSTOMER_PROFILE = '''SELECT c.first_name, c.last_name, c.email, c.phone, 
        TO_CHAR(c.dob, 'YYYY-MM-DD') AS dob, c.gender, c.enabled,
        m.id AS media_id, m.name, m.path
        FROM customers c
        LEFT JOIN media m ON c.dp_id = m.id 
        WHERE c.id= %s'''

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_CUSTOMER_PROFILE, (customer_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            # customer_profile_dict = row._asdict()
            customer_profile_dict['first_name'] = row.first_name
            customer_profile_dict['last_name'] = row.last_name
            customer_profile_dict['email'] = row.email
            customer_profile_dict['phone'] = row.phone
            customer_profile_dict['dob'] = row.dob
            customer_profile_dict['gender'] = row.gender
            customer_profile_dict['enabled'] = row.enabled

            dp_media_dict = {}
            dp_media_dict['id'] = row.media_id
            dp_media_dict['name'] = row.name
            # media_dict['path'] = row.path
            path = row.path
            if path is not None:
                dp_media_dict['path'] = "{}/{}".format(
                    app.config["S3_LOCATION"], path)
            else:
                dp_media_dict['path'] = None
            customer_profile_dict.update({"dp": dp_media_dict})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(customer_profile_dict)
        return customer_profile_dict

    @f_jwt.jwt_required()
    def put(self):
        customer_id = f_jwt.get_jwt_identity().get("customer_id")
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if (not customer_id) and (user_type != 'customer'):
            abort(403, 'Forbidden')

        data = request.get_json()
        customer_dict = json.loads(json.dumps(data))
        # app.logger.debug(customer_dict)

        UPDATE_CUSTOMER_PROFILE = '''UPDATE customers SET first_name= %s, last_name= %s, dob= %s, 
        gender= %s, dp_id= %s, updated_at= %s WHERE id= %s'''
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_CUSTOMER_PROFILE, (customer_dict.get('first_name'), customer_dict.get('last_name'),
                                  customer_dict.get(
                                      'dob'), customer_dict.get('gender'),
                                  customer_dict.get('dp_id'), datetime.now(), customer_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update customers row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"customer_id {customer_id} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self):
        customer_id = f_jwt.get_jwt_identity().get("customer_id")
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if (not customer_id) and (user_type != 'customer'):
            abort(403, 'Forbidden')

        DELETE_USER = 'DELETE FROM users WHERE id= %s AND trashed= True'
        try:
            cursor = app_globals.get_cursor()

            cursor.execute(DELETE_USER, (user_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200


class SellerProfile(Resource):
    @f_jwt.jwt_required()
    def get(self):
        seller_id = f_jwt.get_jwt_identity().get("seller_id")
        app.logger.debug("seller_id= %s", seller_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if (not seller_id) and (user_type != 'seller'):
            abort(403, 'Forbidden')

        seller_profile_dict = {}

        GET_SELLER_PROFILE = '''SELECT s.seller_name, s.email, s.phone, 
        s."GSTIN", s."PAN", s.enabled,
        dm.id AS dp_media_id, dm.name AS dp_media_name, dm.path AS dp_media_path,
        sm.id AS sign_media_id, sm.name AS sign_media_name, sm.path AS sign_media_path 
        FROM sellers s 
        LEFT JOIN media dm ON s.dp_id = dm.id
        LEFT JOIN media sm ON s.sign_id = sm.id
        WHERE s.id= %s'''

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_SELLER_PROFILE, (seller_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            seller_profile_dict['seller_name'] = row.seller_name
            seller_profile_dict['email'] = row.email
            seller_profile_dict['phone'] = row.phone
            seller_profile_dict['GSTIN'] = row.GSTIN
            seller_profile_dict['PAN'] = row.PAN
            seller_profile_dict['enabled'] = row.enabled

            dp_media_dict = {}
            dp_media_dict['id'] = row.dp_media_id
            dp_media_dict['name'] = row.dp_media_name
            # media_dict['path'] = row.dp_media_path
            path = row.dp_media_path
            if path is not None:
                dp_media_dict['path'] = "{}/{}".format(
                    app.config["S3_LOCATION"], path)
            else:
                dp_media_dict['path'] = None
            seller_profile_dict.update({"dp": dp_media_dict})

            sign_media_dict = {}
            sign_media_dict['id'] = row.sign_media_id
            sign_media_dict['name'] = row.sign_media_name
            # media_dict['path'] = row.sign_media_path
            path = row.sign_media_path
            if path is not None:
                sign_media_dict['path'] = "{}/{}".format(
                    app.config["S3_LOCATION"], path)
            else:
                sign_media_dict['path'] = None
            seller_profile_dict.update({"signature": sign_media_dict})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(seller_profile_dict)
        return seller_profile_dict

    @f_jwt.jwt_required()
    def put(self):
        seller_id = f_jwt.get_jwt_identity().get("seller_id")
        app.logger.debug("seller_id= %s", seller_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if (not seller_id) and (user_type != 'seller'):
            abort(403, 'Forbidden')

        data = request.get_json()
        seller_dict = json.loads(json.dumps(data))
        # app.logger.debug(seller_dict)

        UPDATE_SELLER_PROFILE = '''UPDATE sellers SET seller_name= %s, "GSTIN"= %s, "PAN"= %s, 
        dp_id= %s, sign_id= %s, updated_at= %s
        WHERE id= %s'''
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_SELLER_PROFILE, (seller_dict.get('seller_name'), seller_dict.get('GSTIN'),
                                seller_dict.get(
                                    'PAN'), seller_dict.get('dp_id'),
                                seller_dict.get('sign_id'), datetime.now(), seller_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update sellers row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"seller_id {seller_id} modified."}, 200
    
    @f_jwt.jwt_required()
    def delete(self):
        seller_id = f_jwt.get_jwt_identity().get("seller_id")
        app.logger.debug("seller_id= %s", seller_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if (not seller_id) and (user_type != 'seller'):
            abort(403, 'Forbidden')

        DELETE_USER = 'DELETE FROM sellers WHERE id= %s AND trashed= True'
        try:
            cursor = app_globals.get_cursor()

            cursor.execute(DELETE_USER, (seller_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200

class AdminProfile(Resource):
    @f_jwt.jwt_required()
    def get(self):
        admin_id = f_jwt.get_jwt_identity().get("admin_id")
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if (not admin_id) and (user_type != 'admin'):
            abort(403, 'Forbidden')

        admin_profile_dict = {}

        GET_ADMIN_PROFILE = '''SELECT a.first_name, a.last_name, a.email, a.phone, 
        TO_CHAR(a.dob, 'YYYY-MM-DD') AS dob, a.gender, a.enabled,
        m.id AS media_id, m.name, m.path
        FROM admins a
        LEFT JOIN media m ON a.dp_id = m.id 
        WHERE a.id= %s'''

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_ADMIN_PROFILE, (admin_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            # admin_profile_dict = row._asdict()
            admin_profile_dict['first_name'] = row.first_name
            admin_profile_dict['last_name'] = row.last_name
            admin_profile_dict['email'] = row.email
            admin_profile_dict['phone'] = row.phone
            admin_profile_dict['dob'] = row.dob
            admin_profile_dict['gender'] = row.gender
            admin_profile_dict['enabled'] = row.enabled

            dp_media_dict = {}
            dp_media_dict['id'] = row.media_id
            dp_media_dict['name'] = row.name
            # media_dict['path'] = row.path
            path = row.path
            if path is not None:
                dp_media_dict['path'] = "{}/{}".format(
                    app.config["S3_LOCATION"], path)
            else:
                dp_media_dict['path'] = None
            admin_profile_dict.update({"dp": dp_media_dict})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(admin_profile_dict)
        return admin_profile_dict

    @f_jwt.jwt_required()
    def put(self):
        admin_id = f_jwt.get_jwt_identity().get("admin_id")
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if (not admin_id) and (user_type != 'admin'):
            abort(403, 'Forbidden')

        data = request.get_json()
        admin_dict = json.loads(json.dumps(data))
        # app.logger.debug(admin_dict)

        UPDATE_CUSTOMER_PROFILE = '''UPDATE admins SET first_name= %s, last_name= %s, dob= %s, 
        gender= %s, dp_id= %s, updated_at= %s WHERE id= %s'''
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_CUSTOMER_PROFILE, (admin_dict.get('first_name'), admin_dict.get('last_name'),
                                  admin_dict.get(
                                      'dob'), admin_dict.get('gender'),
                                  admin_dict.get('dp_id'), datetime.now(), admin_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update admins row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"admin_id {admin_id} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self):
        admin_id = f_jwt.get_jwt_identity().get("admin_id")
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if (not admin_id) and (user_type != 'admin'):
            abort(403, 'Forbidden')

        DELETE_USER = 'DELETE FROM admins WHERE id= %s AND trashed= True'
        try:
            cursor = app_globals.get_cursor()

            cursor.execute(DELETE_USER, (admin_id,))
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
            # # app.logger.debug("cursor object: %s", cursor)

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
