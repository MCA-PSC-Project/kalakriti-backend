from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Banners(Resource):
    @f_jwt.jwt_required()
    def post(self):
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        media_id = data.get("media_id", None)
        redirect_type = data.get("redirect_type", None)
        redirect_url = data.get("redirect_url", None)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can create banner")

        CREATE_BANNER = '''INSERT INTO banners(media_id, redirect_type, redirect_url)
        VALUES(%s,%s, %s) RETURNING id'''
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                CREATE_BANNER, (media_id, redirect_type, redirect_url,))
            id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return f"banner_id =  {id} created sucessfully", 201

    def get(self):
        banners_list = []

        GET_BANNERS = '''SELECT b.id, b.redirect_type, b.redirect_url,
                        m.id, m.name, m.path 
                        FROM banners b LEFT JOIN media m on b.media_id = m.id
                        '''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_BANNERS)
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                banners_dict = {}
                banners_dict['id'] = row[0]
                banners_dict['redirect_type'] = row[1]
                banners_dict['redirect_url'] = row[2]

                banner_media_dict = {}
                banner_media_dict['id'] = row[3]
                banner_media_dict['name'] = row[4]
                path = row[5]
                if path is not None:
                   banner_media_dict['path'] = "{}/{}".format(
                     app.config["S3_LOCATION"], row[5])
                else:
                   banner_media_dict['path'] = None
                banners_dict.update({"dp": banner_media_dict})

                banners_list.append(banners_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(banner_dict)
        return banners_list

    @ f_jwt.jwt_required()
    def put(self, banner_id):
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        banner_dict = json.loads(json.dumps(data))
        app.logger.debug(banner_dict)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can update banners")

        UPDATE_BANNER = 'UPDATE banners SET redirect_type= %s, redirect_url= %s WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_BANNER, (banner_dict['redirect_type'], banner_dict['redirect_url'], banner_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"Banner_id {banner_id} modified."}, 200

    @ f_jwt.jwt_required()
    def delete(self, banner_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "Only super-admins and admins can delete banner")

        DELETE_BANNER = 'DELETE FROM banners WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            app.logger.debug("cursor object: %s", cursor, "\n")

            cursor.execute(DELETE_BANNER, (banner_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200
