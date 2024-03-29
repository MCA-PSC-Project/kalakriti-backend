from datetime import datetime, timezone
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
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type == "super_admin":
            user_type = "admin"

        data = request.get_json()
        address_dict = json.loads(json.dumps(data))

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        try:
            cursor = app_globals.get_cursor()
            full_name = address_dict.get("full_name")
            mobile_no = address_dict.get("mobile_no")
            if (
                full_name is None
                or full_name == ""
                or mobile_no is None
                or mobile_no == ""
            ):
                GET_FULL_NAME = """SELECT {}, mobile_no FROM {} WHERE id = %s""".format(
                    "first_name || ' ' || last_name"
                    if user_type != "seller"
                    else "seller_name",
                    user_type + "s",
                )
                cursor.execute(GET_FULL_NAME, (user_id,))
                row = cursor.fetchone()
                full_name = row[0]
                mobile_no = row[1]

            ADD_ADDRESS = """INSERT INTO addresses(full_name, mobile_no, address_line1, address_line2, 
            city, district, state, country, pincode, landmark, added_at)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

            cursor.execute(
                ADD_ADDRESS,
                (
                    full_name,
                    mobile_no,
                    address_dict.get("address_line1"),
                    address_dict.get("address_line2"),
                    address_dict.get("city"),
                    address_dict.get("district"),
                    address_dict.get("state"),
                    address_dict.get("country"),
                    address_dict.get("pincode"),
                    address_dict.get("landmark"),
                    datetime.now(timezone.utc),
                ),
            )
            address_id = cursor.fetchone()[0]

            ASSOCIATE_ADDRESS_WITH_USER = """INSERT INTO {0}_addresses({0}_id, address_id) VALUES(%s, %s)""".format(
                user_type
            )

            cursor.execute(
                ASSOCIATE_ADDRESS_WITH_USER,
                (
                    user_id,
                    address_id,
                ),
            )

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            app_globals.db_conn.rollback()
            app_globals.db_conn.autocommit = True
            app.logger.debug("autocommit switched back from off to on")
            abort(400, "Bad Request")
        finally:
            cursor.close()
        app_globals.db_conn.commit()
        app_globals.db_conn.autocommit = True
        return f"address with {address_id} created sucessfully", 201

    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type == "super_admin":
            user_type = "admin"
        addresses_list = []

        GET_ADDRESSES = """SELECT a.id AS address_id, a.full_name, a.mobile_no, 
        a.address_line1, a.address_line2, a.city, a.district, a.state,
        a.country, a.pincode, a.landmark, a.added_at, a.updated_at, ca.is_default
        FROM addresses a
        JOIN {0}_addresses ca ON a.id = ca.address_id
        WHERE ca.{0}_id = %s AND a.trashed = False
        ORDER BY ca.is_default, address_id""".format(
            user_type
        )
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_ADDRESSES, (user_id,))
            rows = cursor.fetchall()
            if not rows:
                return []
            for row in rows:
                address_dict = {}
                address_dict["address_id"] = row.address_id
                address_dict["full_name"] = row.full_name
                address_dict["mobile_no"] = row.mobile_no
                address_dict["address_line1"] = row.address_line1
                address_dict["address_line2"] = row.address_line2
                address_dict["city"] = row.city
                address_dict["district"] = row.district
                address_dict["state"] = row.state
                address_dict["country"] = row.country
                address_dict["pincode"] = row.pincode
                address_dict["landmark"] = row.landmark
                address_dict["is_default"] = row.is_default
                address_dict.update(
                    json.loads(json.dumps({"added_at": row.added_at}, default=str))
                )
                address_dict.update(
                    json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
                )
                addresses_list.append(address_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(addresses_list)
        return addresses_list

    @f_jwt.jwt_required()
    def put(self, address_id):
        app.logger.debug("address_id= %s", address_id)
        data = request.get_json()
        address_dict = json.loads(json.dumps(data))

        UPDATE_ADDRESS = """UPDATE addresses SET full_name= %s, mobile_no= %s, address_line1= %s, address_line2= %s, 
        city= %s, district= %s, state= %s, country= %s, pincode= %s, landmark= %s, updated_at= %s 
        WHERE id= %s"""

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_ADDRESS,
                (
                    address_dict.get("full_name"),
                    address_dict.get("mobile_no"),
                    address_dict.get("address_line1"),
                    address_dict.get("address_line2"),
                    address_dict.get("city"),
                    address_dict.get("district"),
                    address_dict.get("state"),
                    address_dict.get("country"),
                    address_dict.get("pincode"),
                    address_dict.get("landmark"),
                    datetime.now(timezone.utc),
                    address_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update addresses row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"address_id {address_id} modified."}, 200

    @f_jwt.jwt_required()
    def patch(self, address_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)
        app.logger.debug("address_id= %s", address_id)
        data = request.get_json()

        if "trashed" in data.keys():
            trashed = data.get("trashed")
            UPDATE_ADDRESS_TRASHED_VALUE = (
                """UPDATE addresses SET trashed= %s, updated_at= %s WHERE id= %s"""
            )
            try:
                cursor = app_globals.get_cursor()
                cursor.execute(
                    UPDATE_ADDRESS_TRASHED_VALUE,
                    (
                        trashed,
                        datetime.now(timezone.utc),
                        address_id,
                    ),
                )
                if cursor.rowcount != 1:
                    abort(400, "Bad Request: update addresses row error")
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, "Bad Request")
            finally:
                cursor.close()
            return {"message": f"Address id = {address_id} modified."}, 200
        elif "default" in data.keys():
            default = data.get("default")
            MAKE_ADDRESS_DEFAULT = """UPDATE {0}_addresses SET is_default = %s 
            WHERE {0}_id = %s AND address_id = %s""".format(
                user_type
            )
            try:
                cursor = app_globals.get_cursor()
                cursor.execute(
                    MAKE_ADDRESS_DEFAULT,
                    (
                        default,
                        user_id,
                        address_id,
                    ),
                )
                if cursor.rowcount != 1:
                    abort(
                        400,
                        "Bad Request: update {}_addresses row error".format(user_type),
                    )
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, "Bad Request")
            finally:
                cursor.close()
            return {"message": f"Address id = {address_id} set to default"}, 200
        else:
            abort(400, "Bad Request")

    @f_jwt.jwt_required()
    def delete(self, address_id):
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, "Forbidden: only super-admins and admins can delete address")

        try:
            cursor = app_globals.get_cursor()
            DELETE_TRASHED_ADDRESS = (
                "DELETE FROM addresses WHERE id= %s AND trashed = True"
            )
            cursor.execute(DELETE_TRASHED_ADDRESS, (address_id,))
            if cursor.rowcount != 1:
                abort(400, "Bad Request: delete addresses row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return 200
