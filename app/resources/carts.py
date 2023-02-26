from datetime import datetime
import json
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
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
            GET_CART_ID = '''SELECT id from carts WHERE user_id = %s'''
            cursor.execute(
                GET_CART_ID, (user_id,))
            row = cursor.fetchone()
            if not row:
                app.logger.debug("cart_id not found!")
                # app_globals.db_conn.rollback()
                # if there is no cart for the user_id
                CREATE_CART = '''INSERT INTO carts(user_id) RETURNING id'''
                cursor.execute(CREATE_CART, (user_id,))
                row = cursor.fetchone()
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

        GET_ITEMS_IN_CART = '''SELECT ci.cart_id, ci.product_item_id, ci.quantity, 
        p.id, p.product_name, p.currency, p.min_order_quantity, p.max_order_quantity,
        pi.id, pi.product_id, pi.product_variant_name, pi.original_price, pi.offer_price, pi.quantity_in_stock 
        FROM cart_items ci
        JOIN product_items pi ON pi.id = ci.product_item_id
        JOIN products p ON p.id= (SELECT product_id FROM product_items WHERE id= ci.product_item_id)
        WHERE cart_id = (SELECT id FROM carts WHERE user_id =%s)'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)
            cursor.execute(GET_ITEMS_IN_CART, (user_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                carts_dict = {}
                carts_dict['cart_id'] = row[0]
                carts_dict['product_item_id'] = row[1]
                carts_dict['quantity'] = row[2]
                carts_dict['product_id'] = row[3]
                carts_dict['product_name'] = row[4]
                carts_dict['currency'] = row[5]
                carts_dict['min_order_quantity'] = row[6]
                carts_dict['max_order_quantity'] = row[7]

                product_item_dict = {}
                product_item_dict['id'] = row[8]
                product_item_dict['product_id'] = row[9]
                product_item_dict['product_variant_name'] = row[10]

                product_item_dict.update(json.loads(
                    json.dumps({'original_price': row[11]}, default=str)))
                product_item_dict.update(json.loads(
                    json.dumps({'offer_price': row[12]}, default=str)))
                product_item_dict['quantity_in_stock'] = row[13]

                carts_dict.update({"product_item": product_item_dict})

                carts_list.append(carts_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            app_globals.db_conn.rollback()
            app_globals.db_conn.autocommit = True
            app.logger.debug("autocommit switched back from off to on")
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(carts_list)
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
            GET_CART_ID = '''SELECT id FROM carts WHERE user_id = %s '''
            cursor.execute(
                GET_CART_ID, (user_id,))
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
