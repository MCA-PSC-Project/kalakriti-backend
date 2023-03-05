from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class UserAddress(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        address_dict = json.loads(json.dumps(data))
        current_time = datetime.now()

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        # print(app_globals.db_conn)
        # catch exception for invalid SQL statement

        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            ADD_ADDRESS = '''INSERT INTO addresses(address, district, city, state, country, pincode, landmark, added_at)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id'''

            cursor.execute(ADD_ADDRESS, (address_dict.get('address'), address_dict.get('district'),
                                         address_dict.get(
                                             'city'), address_dict.get('state'),
                                         address_dict.get(
                                             'country'), address_dict.get('pincode'),
                                         address_dict.get('landmark'), current_time))
            address_id = cursor.fetchone()[0]

            ASSOCIATE_ADDRESS_WITH_USER = '''INSERT INTO user_addresses(user_id, address_id) VALUES(%s, %s)'''

            cursor.execute(ASSOCIATE_ADDRESS_WITH_USER, (user_id, address_id,))

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            app_globals.db_conn.rollback()
            app_globals.db_conn.autocommit = True
            app.logger.debug("autocommit switched back from off to on")
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        app_globals.db_conn.commit()
        app_globals.db_conn.autocommit = True
        return f"address with {address_id} created sucessfully", 201

    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)

        addresses_list = []

        GET_ADDRESSES = '''SELECT id AS address_id, address, district, city, state, country, pincode, landmark, 
        added_at, updated_at
        FROM addresses WHERE id IN (
            SELECT address_id FROM user_addresses WHERE user_id = %s
        ) AND trashed = False'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            # cursor = app_globals.get_cursor()
            cursor = app_globals.get_named_tuple_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_ADDRESSES, (user_id, ))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                address_dict = {}
                address_dict['address_id'] = row.address_id
                address_dict['address'] = row.address
                address_dict['district'] = row.district
                address_dict['city'] = row.city
                address_dict['state'] = row.state
                address_dict['country'] = row.country
                address_dict['pincode'] = row.pincode
                address_dict['landmark'] = row.landmark
                address_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                address_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))

                addresses_list.append(address_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(addresses_list)
        return addresses_list

    @ f_jwt.jwt_required()
    def put(self, address_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)

        app.logger.debug("address_id= %s", address_id)
        data = request.get_json()
        address_dict = json.loads(json.dumps(data))
        # app.logger.debug(address_dict)

        current_time = datetime.now()

        UPDATE_ADDRESS = '''UPDATE addresses SET address= %s, district= %s, city= %s, state= %s, country= %s, pincode= %s,
        landmark= %s, updated_at= %s WHERE id= %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_ADDRESS, (address_dict.get('address'), address_dict.get('district'),
                                 address_dict.get(
                    'city'), address_dict.get('state'),
                    address_dict.get(
                    'country'), address_dict.get('pincode'),
                    address_dict.get('landmark'), current_time, address_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update addresses row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"address_id {address_id} modified."}, 200

    @f_jwt.jwt_required()
    def patch(self, address_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)

        data = request.get_json()
        if 'trashed' not in data.keys():
            abort(400, 'Bad Request')
        trashed= data.get('trashed')
        current_time = datetime.now()

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            UPDATE_ADDRESS_TRASHED_VALUE = '''UPDATE addresses SET trashed= %s, updated_at= %s WHERE id= %s'''

            cursor.execute(
                UPDATE_ADDRESS_TRASHED_VALUE, (trashed, current_time, address_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update adddresses row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"Address id = {address_id} modified."}, 200
    
    @f_jwt.jwt_required()
    def delete(self, address_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)
        # app.logger.debug("address_id=%s", address_id)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can delete address")

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            DELETE_TRASHED_ADDRESS = 'DELETE FROM addresses WHERE id= %s AND trashed = True'

            cursor.execute(DELETE_TRASHED_ADDRESS, (address_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete addresses row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200
