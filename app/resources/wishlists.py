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
                ADD_TO_WISHLIST, (user_id,product_item_id, current_time,))
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

        GET_WISHLISTS = '''SELECT product_id ,product_variant_name ,"SKU" ,original_price, offer_price 
        FROM product_items 
        WHERE id IN
        (SELECT product_item_id FROM wishlists WHERE user_id =%s )'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)
            cursor.execute(GET_WISHLISTS,str(user_id),)
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                wishlists_dict = {}
                wishlists_dict['product_id'] = row[0]
                wishlists_dict['product_variant_name'] = row[1]
                wishlists_dict['SKU'] = row[2]
                
                wishlists_dict.update(json.loads(
                    json.dumps({'original_price': row[3]}, default=str)))
                wishlists_dict.update(json.loads(
                    json.dumps({'offer_price': row[4]}, default=str)))
                
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

