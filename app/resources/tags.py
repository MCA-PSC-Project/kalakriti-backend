from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Tags(Resource):
    def get(self, product_id):
        if not product_id:
            abort(400, 'Bad Request')

        tags_list = []
        GET_TAGS = '''SELECT tags from products WHERE id= %s'''
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_TAGS, (product_id,))
            row = cursor.fetchone()
            if not row:
                return []
            tags_list = row.tags
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(tags_list)
        return tags_list

    # for both put and delete([]) tags
    @ f_jwt.jwt_required()
    def put(self, product_id):
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        # convert json to list
        tags_list = json.loads(json.dumps(data))
        app.logger.debug(tags_list)

        if user_type != "seller" and user_type != "admin" and user_type != "super_admin":
            abort(400, "only sellers, super-admins and admins can update tags")

        UPDATE_TAGS = '''UPDATE products SET tags= %s WHERE id= %s'''
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_TAGS, (tags_list, product_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"Tags of Product_id {product_id} modified."}, 200
