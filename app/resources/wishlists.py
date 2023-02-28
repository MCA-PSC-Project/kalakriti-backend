from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Wishlists(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        # claims = f_jwt.get_jwt()
        # user_type = claims['user_type']
        # app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        product_item_id = data.get("product_item_id", None)

        current_time = datetime.now()

        ADD_TO_WISHLIST = '''INSERT INTO wishlists(user_id,product_item_id, added_at)
                               VALUES(%s, %s, %s)'''
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                ADD_TO_WISHLIST, (user_id, product_item_id, current_time,))
           # id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return f"Product_item_id = {product_item_id} added to wishilist for user_id {user_id}", 201

    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)

        wishlists_list = []

        GET_WISHLISTS = '''SELECT pi.product_id, pi.id AS product_item_id,
        (SELECT p.product_name FROM products p WHERE p.id = pi.product_id),
        pi.product_variant_name ,pi.original_price, pi.offer_price,
        (SELECT v.variant AS variant FROM variants v WHERE v.id =
        (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
        (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id) 
        FROM product_items pi
        JOIN product_item_values piv ON pi.id = piv.product_item_id
        WHERE pi.id IN
        (SELECT w.product_item_id FROM wishlists w WHERE w.user_id =%s)'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)
            cursor.execute(GET_WISHLISTS, (user_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                wishlists_dict = {}
                wishlists_dict['product_id'] = row.product_id
                wishlists_dict['product_item_id'] = row.product_item_id
                wishlists_dict['product_name'] = row.product_name
                wishlists_dict['product_variant_name'] = row.product_variant_name                
                wishlists_dict.update(json.loads(
                    json.dumps({'original_price': row.original_price}, default=str)))
                wishlists_dict.update(json.loads(
                    json.dumps({'offer_price': row.offer_price}, default=str)))
                wishlists_dict['variant'] = row.variant
                wishlists_dict['variant_value'] = row.variant_value
                wishlists_list.append(wishlists_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(banner_dict)
        return wishlists_list

    @ f_jwt.jwt_required()
    def delete(self, product_item_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        # claims = f_jwt.get_jwt()
        # user_type = claims['user_type']

        REMOVE_FROM_WISHLIST = 'DELETE FROM wishlists WHERE product_item_id= %s AND user_id =%s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(REMOVE_FROM_WISHLIST, (product_item_id, user_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200
