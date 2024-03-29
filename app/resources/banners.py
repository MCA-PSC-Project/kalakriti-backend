from datetime import datetime, timezone
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app

from app.resources.media import delete_media_by_id


class Banners(Resource):
    @f_jwt.jwt_required()
    def post(self):
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        media_id = data.get("media_id", None)
        redirect_type = data.get("redirect_type", None)
        redirect_url = data.get("redirect_url", None)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, "Forbidden: only super-admins and admins can create category")

        CREATE_BANNER = """INSERT INTO banners(media_id, redirect_type, redirect_url)
        VALUES(%s, %s, %s) RETURNING id"""

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                CREATE_BANNER,
                (
                    media_id,
                    redirect_type,
                    redirect_url,
                ),
            )
            id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        app_globals.redis_client.delete("banners")
        return f"banner_id = {id} created sucessfully", 201

    def get(self):
        banners_list = []

        try:
            key_name = "banners"
            # app.logger.debug("keyname= %s", key_name)
            response = app_globals.redis_client.get(key_name)
            # app_globals.redis_client.delete(key_name)
            if response:
                return json.loads(response.decode("utf-8"))
        except Exception as err:
            app.logger.debug(err)

        GET_BANNERS = """SELECT b.id AS banner_id, b.redirect_type, b.redirect_url,
        m.id AS media_id, m.name, m.path 
        FROM banners b LEFT JOIN media m ON b.media_id = m.id"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_BANNERS)
            rows = cursor.fetchall()
            if not rows:
                return []
            for row in rows:
                banners_dict = {}
                banners_dict["id"] = row.banner_id
                banners_dict["redirect_type"] = row.redirect_type
                banners_dict["redirect_url"] = row.redirect_url
                banner_media_dict = {}
                banner_media_dict["id"] = row.media_id
                banner_media_dict["name"] = row.name
                path = row.path
                if path is not None:
                    banner_media_dict["path"] = "{}/{}".format(
                        app.config["S3_LOCATION"], path
                    )
                else:
                    banner_media_dict["path"] = None
                banners_dict.update({"media": banner_media_dict})
                banners_list.append(banners_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        app_globals.redis_client.set(
            key_name,
            json.dumps(banners_list),
        )
        app_globals.redis_client.expire(key_name, 7200)  # seconds
        # app.logger.debug(banners_list)
        return banners_list

    @f_jwt.jwt_required()
    def put(self, banner_id):
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        banner_dict = json.loads(json.dumps(data))
        app.logger.debug(banner_dict)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, "Forbidden: only super-admins and admins can update banner")

        UPDATE_BANNER = """UPDATE banners SET media_id = %s, redirect_type = %s, redirect_url = %s WHERE id = %s
        RETURNING (SELECT media_id FROM banners WHERE id =  %s)"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_BANNER,
                (
                    banner_dict["media_id"],
                    banner_dict["redirect_type"],
                    banner_dict["redirect_url"],
                    banner_id,
                    banner_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update row error")
            old_media_id = cursor.fetchone()[0]
            app.logger.debug("old_media_id= %s", old_media_id)
            if old_media_id and old_media_id != banner_dict.get("media_id"):
                if delete_media_by_id(old_media_id):
                    app.logger.debug(
                        "deleted media from bucket where id= %s", old_media_id
                    )
                else:
                    app.logger.debug(
                        "error occurred in deleting media where id= %s", old_media_id
                    )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        app_globals.redis_client.delete("banners")
        return {"message": f"Banner_id {banner_id} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self, banner_id):
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, "Forbidden: only super-admins and admins can delete banner")

        DELETE_BANNER = """DELETE FROM banners WHERE id = %s 
        RETURNING (SELECT media_id FROM banners WHERE id =  %s)"""

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                DELETE_BANNER,
                (
                    banner_id,
                    banner_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: delete row error")
            old_media_id = cursor.fetchone()[0]
            app.logger.debug("old_media_id= %s", old_media_id)
            if delete_media_by_id(old_media_id):
                app.logger.debug("deleted media from bucket where id= %s", old_media_id)
            else:
                app.logger.debug(
                    "error occurred in deleting media where id= %s", old_media_id
                )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        app_globals.redis_client.delete("banners")
        return 200
