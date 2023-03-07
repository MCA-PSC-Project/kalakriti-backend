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
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        # args = request.args  # retrieve args from query string
        # user = args.get('user', None)
        # app.logger.debug("?user=%s", user)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can view all sellers")

        seller_list = []

        GET_SELLERS_PROFILES = '''SELECT s.seller_name, u.user_type, u.email, u.phone, 
        s."GSTIN", s."PAN", u.enabled,
        m.id AS media_id, m.name AS media_name, m.path
        FROM users u
        JOIN sellers s ON u.id = s.user_id
        LEFT JOIN media m on u.dp_id = m.id WHERE u.user_type= %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_SELLERS_PROFILES, ('seller',))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                seller_profile_dict = {}
                seller_profile_dict['seller_name'] = row.seller_name
                seller_profile_dict['user_type'] = row.user_type
                seller_profile_dict['email'] = row.email
                seller_profile_dict['phone'] = row.phone
                seller_profile_dict['GSTIN'] = row.GSTIN
                seller_profile_dict['PAN'] = row.PAN
                seller_profile_dict['enabled'] = row.enabled

                dp_media_dict = {}
                dp_media_dict['id'] = row.media_id
                dp_media_dict['name'] = row.media_name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    dp_media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    dp_media_dict['path'] = None
                seller_profile_dict.update({"dp": dp_media_dict})
                seller_list.append(seller_profile_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(seller_list)
        return seller_list


class GetCustomers(Resource):
    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can view all customers")


        customer_list = []

        GET_CUSTOMERS_PROFILES = '''SELECT u.first_name, u.last_name, u.user_type, u.email, u.phone, 
        TO_CHAR(u.dob, 'YYYY-MM-DD'), u.gender , u.enabled,
        m.id AS media_id, m.name AS media_name, m.path
        FROM users u 
        LEFT JOIN media m ON u.dp_id = m.id 
        WHERE user_type= %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_CUSTOMERS_PROFILES, ('customer',))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                customer_profile_dict = {}
                customer_profile_dict['first_name'] = row.first_name
                customer_profile_dict['last_name'] = row.last_name
                customer_profile_dict['user_type'] = row.user_type
                customer_profile_dict['email'] = row.email
                customer_profile_dict['phone'] = row.phone
                customer_profile_dict['dob'] = row.dob
                customer_profile_dict['gender'] = row.gender
                customer_profile_dict['enabled'] = row.enabled

                dp_media_dict = {}
                dp_media_dict['id'] = row.media_id
                dp_media_dict['name'] = row.media_name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    dp_media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    dp_media_dict['path'] = None
                customer_profile_dict.update({"dp": dp_media_dict})
                customer_list.append(customer_profile_dict)

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(customer_list)
        return customer_list


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
