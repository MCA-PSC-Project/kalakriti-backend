from datetime import datetime, timezone
import json
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app

from app.resources.seller import get_seller_info


class Cart(Resource):
    @f_jwt.jwt_required()
    def post(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        data = request.get_json()
        product_item_id = data.get("product_item_id", None)
        quantity = data.get("quantity", None)
        current_time = datetime.now(timezone.utc)

        app_globals.db_conn.autocommit = False
        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_CART_ID = """SELECT id from carts WHERE customer_id = %s"""
            cursor.execute(GET_CART_ID, (customer_id,))
            row = cursor.fetchone()
            if not row:
                app.logger.debug(
                    "cart_id not found!..Creating a cart for user_id =%s", customer_id
                )
                # if there is no cart for the respective customer_id
                CREATE_CART = (
                    """INSERT INTO carts(customer_id) VALUES(%s) RETURNING id"""
                )
                cursor.execute(CREATE_CART, (customer_id,))
                row = cursor.fetchone()
            cart_id = row[0]

            # the RETURNING clause is used to return the value of the quantity column after the
            # INSERT or UPDATE operation is performed.
            # If an INSERT operation is performed, the value returned will be the value that was inserted.
            # If an UPDATE operation is performed, the value returned will be the updated value of the quantity column.

            GET_QUANTITY_IN_STOCK = (
                """SELECT quantity_in_stock FROM product_items WHERE id = %s"""
            )

            cursor.execute(GET_QUANTITY_IN_STOCK, (product_item_id,))
            quantity_in_stock = cursor.fetchone().quantity_in_stock

            # ADD_TO_CART = """INSERT INTO cart_items(cart_id, product_item_id, quantity, added_at)
            # VALUES(%s, %s, %s, %s) ON CONFLICT (cart_id, product_item_id)
            # DO UPDATE SET quantity = cart_items.quantity + 1, updated_at = %s RETURNING quantity"""

            ADD_TO_CART = """INSERT INTO cart_items(cart_id, product_item_id, quantity, added_at)
            VALUES(%s, %s, %s, %s) ON CONFLICT (cart_id, product_item_id)
            DO UPDATE SET quantity = CASE WHEN cart_items.quantity + 1 <= %s
            THEN cart_items.quantity + 1 END,
            updated_at = %s
            RETURNING quantity"""

            cursor.execute(
                ADD_TO_CART,
                (
                    cart_id,
                    product_item_id,
                    quantity,
                    current_time,
                    quantity_in_stock,
                    current_time,
                ),
            )
            returned_quantity = cursor.fetchone().quantity
            if returned_quantity != quantity:
                # Quantity was updated
                return_string = f"""Quantity increased by 1 for Product_item_id = {product_item_id} for customer_id = {customer_id}"""
                return_status_code = 200
            elif returned_quantity == quantity:
                # Quantity was inserted
                return_string = f"""Product_item_id = {product_item_id} added to cart for customer_id = {customer_id}"""
                return_status_code = 201

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
        return (return_string, return_status_code)

    @f_jwt.jwt_required()
    def get(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", customer_id)

        carts_list = []
        GET_ITEMS_IN_CART = """SELECT ci.cart_id AS cart_id, ci.quantity, ci.added_at, ci.updated_at,
        p.id AS product_id, p.product_name, p.currency, p.min_order_quantity, p.max_order_quantity,
        pi.id AS product_item_id, pi.product_variant_name, pi.original_price, pi.offer_price, pi.quantity_in_stock 
        FROM cart_items ci
        JOIN product_items pi ON pi.id = ci.product_item_id
        JOIN products p ON p.id= (SELECT product_id FROM product_items WHERE id= ci.product_item_id)
        WHERE cart_id = (SELECT id FROM carts WHERE customer_id =%s)
        ORDER BY ci.added_at DESC"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_ITEMS_IN_CART, (customer_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                carts_dict = {}
                carts_dict["cart_id"] = row.cart_id
                carts_dict["quantity"] = row.quantity
                carts_dict.update(
                    json.loads(json.dumps({"added_at": row.added_at}, default=str))
                )
                carts_dict.update(
                    json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
                )
                carts_dict["product_id"] = row.product_id
                carts_dict["product_name"] = row.product_name
                carts_dict["currency"] = row.currency
                carts_dict["min_order_quantity"] = row.min_order_quantity
                carts_dict["max_order_quantity"] = row.max_order_quantity

                product_item_dict = {}
                product_item_dict["id"] = row.product_item_id
                product_item_dict["product_variant_name"] = row.product_variant_name

                product_item_dict.update(
                    json.loads(
                        json.dumps({"original_price": row.original_price}, default=str)
                    )
                )
                product_item_dict.update(
                    json.loads(
                        json.dumps({"offer_price": row.offer_price}, default=str)
                    )
                )
                product_item_dict["quantity_in_stock"] = row.quantity_in_stock

                carts_dict.update(
                    {"seller": get_seller_info(cursor, carts_dict["product_id"])}
                )
                media_dict = {}
                GET_BASE_MEDIA = """SELECT m.id AS media_id, m.name, m.path
                FROM media m
                WHERE m.id = (SELECT pim.media_id From product_item_medias pim
                WHERE pim.product_item_id = %s 
                ORDER BY pim.display_order LIMIT 1) 
                """
                cursor.execute(GET_BASE_MEDIA, (product_item_dict["id"],))
                row = cursor.fetchone()
                if row is None:
                    app.logger.debug("No media rows")
                    product_item_dict.update({"media": media_dict})
                    carts_dict.update({"product_item": product_item_dict})
                    carts_list.append(carts_dict)
                    continue
                media_dict["id"] = row.media_id
                media_dict["name"] = row.name
                path = row.path
                if path is not None:
                    media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
                else:
                    media_dict["path"] = None
                product_item_dict.update({"media": media_dict})
                carts_dict.update({"product_item": product_item_dict})
                carts_list.append(carts_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            app_globals.db_conn.rollback()
            app_globals.db_conn.autocommit = True
            app.logger.debug("autocommit switched back from off to on")
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(carts_list)
        return carts_list

    @f_jwt.jwt_required()
    def patch(self, product_item_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        data = request.get_json()
        quantity = data.get("quantity", None)
        if not quantity:
            abort(400, "Bad Request")
        current_time = datetime.now(timezone.utc)

        GET_CART_ID = """SELECT id from carts WHERE customer_id = %s"""
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_CART_ID, (customer_id,))
            row = cursor.fetchone()
            if not row:
                app.logger.debug("cart_id not found!")
                abort(400, "Bad Request")
            cart_id = row[0]

            GET_QUANTITY_IN_STOCK = (
                """SELECT quantity_in_stock FROM product_items WHERE id = %s"""
            )

            cursor.execute(GET_QUANTITY_IN_STOCK, (product_item_id,))
            quantity_in_stock = cursor.fetchone().quantity_in_stock

            if quantity > quantity_in_stock:
                app.logger.debug("Bad Request: quantiy > quantity_in_stock")
                abort(400, "Bad Request: quantiy > quantity_in_stock")
                
            UPDATE_QUANTITY = """UPDATE cart_items SET quantity= %s, updated_at= %s 
            WHERE cart_id= %s AND product_item_id= %s"""

            cursor.execute(
                UPDATE_QUANTITY, (quantity, current_time, cart_id, product_item_id)
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"Quantity modified for cart_id = {cart_id}."}, 200

    @f_jwt.jwt_required()
    def delete(self, product_item_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        try:
            cursor = app_globals.get_cursor()
            GET_CART_ID = """SELECT id FROM carts WHERE customer_id = %s """
            cursor.execute(GET_CART_ID, (customer_id,))
            row = cursor.fetchone()
            if not row:
                app.logger.debug("cart_id not found!")
                app_globals.db_conn.rollback()
            cart_id = row[0]

            REMOVE_FROM_CART = (
                "DELETE FROM cart_items WHERE product_item_id= %s AND cart_id = %s"
            )
            cursor.execute(
                REMOVE_FROM_CART,
                (
                    product_item_id,
                    cart_id,
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


class CartItemsQuantity(Resource):
    @f_jwt.jwt_required()
    def get(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        GET_NO_OF_ITEMS = """SELECT count(*) AS count FROM cart_items WHERE cart_id = 
            (SELECT id FROM carts WHERE customer_id = %s)"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(GET_NO_OF_ITEMS, (customer_id,))
            row = cursor.fetchone()
            if row is None:
                return 0
            quantity = row[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return quantity
