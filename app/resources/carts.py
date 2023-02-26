from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app

class Carts(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        # claims = f_jwt.get_jwt()
        # user_type = claims['user_type']
        # app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        product_item_id = data.get("product_item_id", None)
        quantity = data.get("quantity", None)

        app_globals.db_conn.autocommit = False
    # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
                # # app.logger.debug("cursor object: %s", cursor)
            GET_CART_ID = '''SELECT id from carts WHERE user_id = %s '''
            cursor.execute(
                GET_CART_ID, (str(user_id),))
            row = cursor.fetchone()
            if not row:
                app.logger.debug("cart_id not found!")
                app_globals.db_conn.rollback()
            cart_id = row[0]

            current_time = datetime.now()

            ADD_TO_CART = '''INSERT INTO cart_items(cart_id,product_item_id,quantity, added_at)
                                VALUES(%s,%s,%s,%s)'''

            cursor.execute(
                ADD_TO_CART, (cart_id, product_item_id, quantity, current_time,))
           # id = cursor.fetchone()[0]
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
        return f"Product_item_id = {product_item_id} added to cart for user_id {user_id}", 201
    
    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)

        carts_list = []

        GET_CARTS = '''SELECT product_item_id, quantity FROM cart_items 
        WHERE cart_id = (SELECT id FROM carts WHERE user_id =%s )'''
        app_globals.db_conn.autocommit = False
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)
            cursor.execute(GET_CARTS,str(user_id),)
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                carts_dict = {}
                # carts_dict['cart_id'] = row[0]
                carts_dict['product_item_id'] = row[0]
                # carts_dict['product_id'] = row[2]
                # carts_dict['product_name'] = row[3] 
                # carts_dict['product_variant_name'] = row[4]
                # carts_dict['SKU'] = row[5]
                # carts_dict.update(json.loads(
                #     json.dumps({'original_price': row[6]}, default=str)))
                # carts_dict.update(json.loads(
                #     json.dumps({'offer_price': row[7]}, default=str)))
                carts_dict['quantity'] = row[1]
                
                carts_list.append(carts_dict)
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
        # app.logger.debug(banner_dict)
        return carts_list


    @ f_jwt.jwt_required()
    def delete(self, product_item_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        # claims = f_jwt.get_jwt()
        # user_type = claims['user_type']
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
                # # app.logger.debug("cursor object: %s", cursor)
            GET_CART_ID = '''SELECT id from carts WHERE user_id = %s '''
            cursor.execute(
                GET_CART_ID, (str(user_id),))
            row = cursor.fetchone()
            if not row:
                app.logger.debug("cart_id not found!")
                app_globals.db_conn.rollback()
            cart_id = row[0]

            REMOVE_FROM_CART = 'DELETE FROM cart_items WHERE product_item_id= %s AND cart_id = %s'

            cursor.execute(REMOVE_FROM_CART, (product_item_id, cart_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200

