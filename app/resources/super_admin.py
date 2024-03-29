from datetime import datetime, timezone
import json
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
from flask import current_app as app


class AdminsInfo(Resource):
    @f_jwt.jwt_required()
    def get(self):
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "super_admin":
            abort(403, "Forbidden: only super-admins can view all admins")

        admins_list = []
        GET_ADMINS_PROFILES = """SELECT a.id, a.first_name, a.last_name, a.email, a.mobile_no, 
        TO_CHAR(a.dob, 'YYYY-MM-DD') AS dob, a.gender , a.enabled, a.is_verified, a.is_super_admin,
        m.id AS media_id, m.name AS media_name, m.path
        FROM admins a 
        LEFT JOIN media m ON a.dp_id = m.id 
        ORDER BY a.id DESC"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_ADMINS_PROFILES, ())
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                admin_profile_dict = {}
                admin_profile_dict["id"] = row.id
                admin_profile_dict["first_name"] = row.first_name
                admin_profile_dict["last_name"] = row.last_name
                admin_profile_dict["email"] = row.email
                admin_profile_dict["mobile_no"] = row.mobile_no
                admin_profile_dict["dob"] = row.dob
                admin_profile_dict["gender"] = row.gender
                admin_profile_dict["enabled"] = row.enabled
                admin_profile_dict["is_verified"] = row.is_verified
                admin_profile_dict["is_super_admin"] = row.is_super_admin

                dp_media_dict = {}
                dp_media_dict["id"] = row.media_id
                dp_media_dict["name"] = row.media_name
                path = row.path
                if path is not None:
                    dp_media_dict["path"] = "{}/{}".format(
                        app.config["S3_LOCATION"], path
                    )
                else:
                    dp_media_dict["path"] = None
                admin_profile_dict.update({"dp": dp_media_dict})
                admins_list.append(admin_profile_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(admins_list)
        return admins_list

    # enable/disable admin
    @f_jwt.jwt_required()
    def patch(self, admin_id):
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "super_admin":
            abort(403, "Forbidden: only super-admins can enable/disable admin")

        data = request.get_json()
        enabled = data.get("enabled", None)

        UPDATE_ADMIN_ENABLED_STATUS = (
            """UPDATE admins SET enabled= %s, updated_at= %s where id= %s"""
        )
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_ADMIN_ENABLED_STATUS,
                (
                    enabled,
                    datetime.now(timezone.utc),
                    str(admin_id),
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"{admin_id} modified"}, 200

    @f_jwt.jwt_required()
    def delete(self, admin_id):
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "super_admin":
            abort(403, "Forbidden: only super-admins can delete admin account")

        DELETE_ADMIN = "DELETE FROM admins WHERE id= %s AND trashed= True"
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(DELETE_ADMIN, (admin_id,))
            if cursor.rowcount != 1:
                abort(400, "Bad Request: delete row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return 200


# Deprecated
class PromoteToAdmin(Resource):
    @f_jwt.jwt_required()
    def put(self):
        # user_id = f_jwt.get_jwt_identity()
        # app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        email = data.get("email", None)

        if user_type != "super_admin":
            abort(400, "only super_admins have privilege to promote to admin")

        current_time = datetime.now(timezone.utc)

        UPDATE_USER_ENABLED_STATUS = (
            """UPDATE users SET user_type= %s, updated_at= %s where email = %s"""
        )

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_USER_ENABLED_STATUS,
                (
                    "admin",
                    current_time,
                    email,
                ),
            )
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update row error")

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()

        return {"message": f"{email} is now admin"}, 200
