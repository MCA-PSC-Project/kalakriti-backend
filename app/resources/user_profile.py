from datetime import datetime, timezone
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app
import app.resources.media as media


class CustomerProfile(Resource):
    @f_jwt.jwt_required()
    def get(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "customer":
            abort(403, "Forbidden")

        customer_profile_dict = {}

        GET_CUSTOMER_PROFILE = """SELECT c.first_name, c.last_name, c.email, c.mobile_no,
        TO_CHAR(c.dob, 'YYYY-MM-DD') AS dob, c.gender, c.enabled,
        m.id AS media_id, m.name, m.path
        FROM customers c
        LEFT JOIN media m ON c.dp_id = m.id
        WHERE c.id= %s"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_CUSTOMER_PROFILE, (customer_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, "Bad Request")
            # customer_profile_dict = row._asdict()
            customer_profile_dict["first_name"] = row.first_name
            customer_profile_dict["last_name"] = row.last_name
            customer_profile_dict["email"] = row.email
            customer_profile_dict["mobile_no"] = row.mobile_no
            customer_profile_dict["dob"] = row.dob
            customer_profile_dict["gender"] = row.gender
            customer_profile_dict["enabled"] = row.enabled

            dp_media_dict = {}
            dp_media_dict["id"] = row.media_id
            dp_media_dict["name"] = row.name
            # media_dict['path'] = row.path
            path = row.path
            if path is not None:
                dp_media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
            else:
                dp_media_dict["path"] = None
            customer_profile_dict.update({"dp": dp_media_dict})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(customer_profile_dict)
        return customer_profile_dict

    @f_jwt.jwt_required()
    def put(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "customer":
            abort(403, "Forbidden")

        data = request.get_json()
        customer_dict = json.loads(json.dumps(data))
        # app.logger.debug(customer_dict)

        UPDATE_CUSTOMER_PROFILE = """UPDATE customers SET first_name= %s, last_name= %s, dob= %s,
        gender= %s, updated_at= %s WHERE id= %s"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_CUSTOMER_PROFILE,
                (
                    customer_dict.get("first_name"),
                    customer_dict.get("last_name"),
                    customer_dict.get("dob"),
                    customer_dict.get("gender"),
                    datetime.now(timezone.utc),
                    customer_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update customers row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"customer_id {customer_id} modified."}, 200

    # for dp update
    @f_jwt.jwt_required()
    def patch(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "customer":
            abort(403, "Forbidden")

        data = request.get_json()
        customer_dict = json.loads(json.dumps(data))
        # app.logger.debug(customer_dict)

        UPDATE_CUSTOMER_PROFILE = """UPDATE customers SET dp_id= %s, updated_at= %s WHERE id= %s 
        RETURNING (SELECT dp_id FROM customers WHERE id =  %s)"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_CUSTOMER_PROFILE,
                (
                    customer_dict.get("dp_id"),
                    datetime.now(timezone.utc),
                    customer_id,
                    customer_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update customers row error")
            old_dp_id = cursor.fetchone()[0]
            app.logger.debug("old_dp_id= %s", old_dp_id)
            if old_dp_id and old_dp_id != customer_dict.get("dp_id"):
                if media.delete_media_by_id(old_dp_id):
                    app.logger.debug(
                        "deleted media from bucket where id= %s", old_dp_id
                    )
                else:
                    app.logger.debug(
                        "error occurred in deleting media where id= %s", old_dp_id
                    )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"customer_id {customer_id} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "customer":
            abort(403, "Forbidden")
        data = request.get_json()
        if "trashed" not in data.keys():
            abort(400, "Bad Request")
        trashed = data.get("trashed")

        MARK_CUSTOMER_AS_TRASHED = "UPDATE customers SET trashed= %s WHERE id= %s"
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                MARK_CUSTOMER_AS_TRASHED,
                (
                    trashed,
                    customer_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return 200


class SellerProfile(Resource):
    @f_jwt.jwt_required()
    def get(self):
        seller_id = f_jwt.get_jwt_identity()
        app.logger.debug("seller_id= %s", seller_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "seller":
            abort(403, "Forbidden")

        seller_profile_dict = {}

        GET_SELLER_PROFILE = """SELECT s.seller_name, s.email, s.mobile_no,
        s."GSTIN", s."PAN", s.enabled,
        dm.id AS dp_media_id, dm.name AS dp_media_name, dm.path AS dp_media_path,
        sm.id AS sign_media_id, sm.name AS sign_media_name, sm.path AS sign_media_path
        FROM sellers s
        LEFT JOIN media dm ON s.dp_id = dm.id
        LEFT JOIN media sm ON s.sign_id = sm.id
        WHERE s.id= %s"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_SELLER_PROFILE, (seller_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, "Bad Request")
            seller_profile_dict["seller_name"] = row.seller_name
            seller_profile_dict["email"] = row.email
            seller_profile_dict["mobile_no"] = row.mobile_no
            seller_profile_dict["GSTIN"] = row.GSTIN
            seller_profile_dict["PAN"] = row.PAN
            seller_profile_dict["enabled"] = row.enabled

            dp_media_dict = {}
            dp_media_dict["id"] = row.dp_media_id
            dp_media_dict["name"] = row.dp_media_name
            # media_dict['path'] = row.dp_media_path
            path = row.dp_media_path
            if path is not None:
                dp_media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
            else:
                dp_media_dict["path"] = None
            seller_profile_dict.update({"dp": dp_media_dict})

            sign_media_dict = {}
            sign_media_dict["id"] = row.sign_media_id
            sign_media_dict["name"] = row.sign_media_name
            # media_dict['path'] = row.sign_media_path
            path = row.sign_media_path
            if path is not None:
                sign_media_dict["path"] = "{}/{}".format(
                    app.config["S3_LOCATION"], path
                )
            else:
                sign_media_dict["path"] = None
            seller_profile_dict.update({"signature": sign_media_dict})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(seller_profile_dict)
        return seller_profile_dict

    @f_jwt.jwt_required()
    def put(self):
        seller_id = f_jwt.get_jwt_identity()
        app.logger.debug("seller_id= %s", seller_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "seller":
            abort(403, "Forbidden")

        data = request.get_json()
        seller_dict = json.loads(json.dumps(data))
        # app.logger.debug(seller_dict)

        UPDATE_SELLER_PROFILE = """UPDATE sellers SET seller_name= %s, "GSTIN"= %s, "PAN"= %s, 
        updated_at= %s WHERE id= %s"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_SELLER_PROFILE,
                (
                    seller_dict.get("seller_name"),
                    seller_dict.get("GSTIN"),
                    seller_dict.get("PAN"),
                    datetime.now(timezone.utc),
                    seller_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update sellers row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"seller_id {seller_id} modified."}, 200

    # for dp or sign update
    @f_jwt.jwt_required()
    def patch(self):
        seller_id = f_jwt.get_jwt_identity()
        app.logger.debug("seller_id= %s", seller_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "seller":
            abort(403, "Forbidden")

        data = request.get_json()
        seller_dict = json.loads(json.dumps(data))
        # app.logger.debug(seller_dict)
        dp_id = seller_dict.get("dp_id", None)
        sign_id = seller_dict.get("sign_id", None)
        if (not dp_id) and sign_id:
            column_name = "sign_id"
            column_value = sign_id
        elif (not sign_id) and dp_id:
            column_name = "dp_id"
            column_value = dp_id
        else:
            app.logger.debug("only either of dp_id or sign_id allowed!")
            abort(400, "Bad Request")

        UPDATE_SELLER_PROFILE = """UPDATE sellers SET {0}= %s, updated_at= %s WHERE id= %s 
        RETURNING (SELECT {0} FROM sellers WHERE id =  %s)""".format(
            column_name
        )
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_SELLER_PROFILE,
                (
                    column_value,
                    datetime.now(timezone.utc),
                    seller_id,
                    seller_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update sellers row error")
            old_column_value = cursor.fetchone()[0]
            app.logger.debug("old_%s = %s", column_name, old_column_value)
            if old_column_value and old_column_value != column_value:
                if media.delete_media_by_id(old_column_value):
                    app.logger.debug(
                        "deleted media from bucket where id= %s", old_column_value
                    )
                else:
                    app.logger.debug(
                        "error occurred in deleting media where id= %s",
                        old_column_value,
                    )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"seller_id {seller_id} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self):
        seller_id = f_jwt.get_jwt_identity()
        app.logger.debug("seller_id= %s", seller_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "seller":
            abort(403, "Forbidden")
        data = request.get_json()
        if "trashed" not in data.keys():
            abort(400, "Bad Request")
        trashed = data.get("trashed")

        MARK_SELLER_AS_TRASHED = "UPDATE sellers SET trashed= %s WHERE id= %s"
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                MARK_SELLER_AS_TRASHED,
                (
                    trashed,
                    seller_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return 200


class AdminProfile(Resource):
    @f_jwt.jwt_required()
    def get(self):
        admin_id = f_jwt.get_jwt_identity()
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin":
            abort(403, "Forbidden")

        admin_profile_dict = {}

        GET_ADMIN_PROFILE = """SELECT a.first_name, a.last_name, a.email, a.mobile_no,
        TO_CHAR(a.dob, 'YYYY-MM-DD') AS dob, a.gender, a.enabled,
        m.id AS media_id, m.name, m.path
        FROM admins a
        LEFT JOIN media m ON a.dp_id = m.id
        WHERE a.id= %s"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_ADMIN_PROFILE, (admin_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, "Bad Request")
            # admin_profile_dict = row._asdict()
            admin_profile_dict["first_name"] = row.first_name
            admin_profile_dict["last_name"] = row.last_name
            admin_profile_dict["email"] = row.email
            admin_profile_dict["mobile_no"] = row.mobile_no
            admin_profile_dict["dob"] = row.dob
            admin_profile_dict["gender"] = row.gender
            admin_profile_dict["enabled"] = row.enabled

            dp_media_dict = {}
            dp_media_dict["id"] = row.media_id
            dp_media_dict["name"] = row.name
            # media_dict['path'] = row.path
            path = row.path
            if path is not None:
                dp_media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
            else:
                dp_media_dict["path"] = None
            admin_profile_dict.update({"dp": dp_media_dict})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(admin_profile_dict)
        return admin_profile_dict

    @f_jwt.jwt_required()
    def put(self):
        admin_id = f_jwt.get_jwt_identity()
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin":
            abort(403, "Forbidden")

        data = request.get_json()
        admin_dict = json.loads(json.dumps(data))
        # app.logger.debug(admin_dict)

        UPDATE_ADMIN_PROFILE = """UPDATE admins SET first_name= %s, last_name= %s, dob= %s,
        gender= %s, updated_at= %s WHERE id= %s"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_ADMIN_PROFILE,
                (
                    admin_dict.get("first_name"),
                    admin_dict.get("last_name"),
                    admin_dict.get("dob"),
                    admin_dict.get("gender"),
                    datetime.now(timezone.utc),
                    admin_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update admins row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"admin_id {admin_id} modified."}, 200

    # for dp update
    @f_jwt.jwt_required()
    def patch(self):
        admin_id = f_jwt.get_jwt_identity()
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin":
            abort(403, "Forbidden")

        data = request.get_json()
        admin_dict = json.loads(json.dumps(data))
        # app.logger.debug(admin_dict)

        UPDATE_ADMIN_PROFILE = """UPDATE admins SET dp_id= %s, updated_at= %s WHERE id= %s 
        RETURNING (SELECT dp_id FROM admins WHERE id =  %s)"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_ADMIN_PROFILE,
                (
                    admin_dict.get("dp_id"),
                    datetime.now(timezone.utc),
                    admin_id,
                    admin_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update admins row error")
            old_dp_id = cursor.fetchone()[0]
            app.logger.debug("old_dp_id= %s", old_dp_id)
            if old_dp_id and old_dp_id != admin_dict.get("dp_id"):
                if media.delete_media_by_id(old_dp_id):
                    app.logger.debug(
                        "deleted media from bucket where id= %s", old_dp_id
                    )
                else:
                    app.logger.debug(
                        "error occurred in deleting media where id= %s", old_dp_id
                    )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"admin_id {admin_id} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self):
        admin_id = f_jwt.get_jwt_identity()
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin":
            abort(403, "Forbidden")
        data = request.get_json()
        if "trashed" not in data.keys():
            abort(400, "Bad Request")
        trashed = data.get("trashed")

        MARK_ADMIN_AS_TRASHED = "UPDATE admins SET trashed= %s WHERE id= %s"
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                MARK_ADMIN_AS_TRASHED,
                (
                    trashed,
                    admin_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: delete row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return 200
