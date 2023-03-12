from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class GetSellers(Resource):
    @f_jwt.jwt_required()
    def get(self):
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, "Forbidden: only super-admins and admins can view all sellers")

        sellers_list = []

        GET_SELLERS_PROFILES = '''SELECT s.seller_name, s.email, s.phone,
        s."GSTIN", s."PAN", s.enabled,
        m.id AS media_id, m.name AS media_name, m.path
        FROM sellers s
        LEFT JOIN media m ON s.id = m.id
        ORDER BY s.id DESC'''

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_SELLERS_PROFILES, ('seller',))
            rows = cursor.fetchall()
            if not rows:
                return []
            for row in rows:
                seller_profile_dict = {}
                seller_profile_dict['seller_name'] = row.seller_name
                seller_profile_dict['email'] = row.email
                seller_profile_dict['phone'] = row.phone
                seller_profile_dict['GSTIN'] = row.GSTIN
                seller_profile_dict['PAN'] = row.PAN
                seller_profile_dict['enabled'] = row.enabled

                dp_media_dict = {}
                dp_media_dict['id'] = row.media_id
                dp_media_dict['name'] = row.media_name
                path = row.path
                if path is not None:
                    dp_media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    dp_media_dict['path'] = None
                seller_profile_dict.update({"dp": dp_media_dict})
                sellers_list.append(seller_profile_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(sellers_list)
        return sellers_list


class GetCustomers(Resource):
    @f_jwt.jwt_required()
    def get(self):
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can view all customers")

        customers_list = []

        GET_CUSTOMERS_PROFILES = '''SELECT c.first_name, c.last_name, c.email, c.phone, 
        TO_CHAR(c.dob, 'YYYY-MM-DD') AS dob, c.gender , c.enabled,
        m.id AS media_id, m.name AS media_name, m.path
        FROM customers c 
        LEFT JOIN media m ON c.dp_id = m.id 
        ORDER BY c.id DESC'''

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_CUSTOMERS_PROFILES, ('customer',))
            rows = cursor.fetchall()
            if not rows:
                return []
            for row in rows:
                customer_profile_dict = {}
                customer_profile_dict['first_name'] = row.first_name
                customer_profile_dict['last_name'] = row.last_name
                customer_profile_dict['email'] = row.email
                customer_profile_dict['phone'] = row.phone
                customer_profile_dict['dob'] = row.dob
                customer_profile_dict['gender'] = row.gender
                customer_profile_dict['enabled'] = row.enabled

                dp_media_dict = {}
                dp_media_dict['id'] = row.media_id
                dp_media_dict['name'] = row.media_name
                path = row.path
                if path is not None:
                    dp_media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    dp_media_dict['path'] = None
                customer_profile_dict.update({"dp": dp_media_dict})
                customers_list.append(customer_profile_dict)

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(customers_list)
        return customers_list


class EnableDisableUser(Resource):
    @f_jwt.jwt_required()
    def put(self, users_id):
        # user_id = f_jwt.get_jwt_identity()
        # app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        user_dict = json.loads(json.dumps(data))
        app.logger.debug(user_dict)

        current_time = datetime.now()

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can update categories")

        UPDATE_USER_ENABLED_STATUS = '''UPDATE users SET enabled= %s, updated_at= %s where id = %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_USER_ENABLED_STATUS, (user_dict['enabled'], current_time, users_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        return {"message": f"user_id {users_id} modified"}, 200


class PromoteToSeller(Resource):
    @f_jwt.jwt_required()
    def put(self):
        # user_id = f_jwt.get_jwt_identity()
        # app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        email = data.get("email", None)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can promote to seller")

        current_time = datetime.now()

        PROMOTE_TO_SELLER = '''UPDATE users SET user_type= %s, updated_at= %s where email = %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(PROMOTE_TO_SELLER, ('seller', current_time, email,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        return {"message": f"{email} is now seller"}, 200
