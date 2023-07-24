from datetime import datetime, timezone
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app

from app.resources.seller import get_seller_info


class Orders(Resource):
    @f_jwt.jwt_required()
    def post(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        # app.logger.debug("user_type= %s", user_type)
        if user_type != "customer":
            abort(403, "Forbidden: only customers can create orders")

        data = request.get_json()
        order_dict = json.loads(json.dumps(data))
        current_time = datetime.now(timezone.utc)
        order_dict["total_original_price"] = 0
        order_dict["sub_total"] = 0
        order_dict["total_discount"] = 0
        order_dict["total_tax"] = 0

        if order_dict.get("checkout_from_cart") == True:
            checkout_from = "cart"
        elif order_dict.get("checkout_from_cart") == False:
            checkout_from = "buy_now"
        else:
            abort(400, "checkout_from_cart not passed correctly")

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        try:
            for order_item_dict in order_dict["order_items"]:
                product_item_id = order_item_dict.get("product_item_id")
                cursor = app_globals.get_named_tuple_cursor()

                GET_PRICE_AND_QTY_IN_STOCK = """SELECT original_price, offer_price, product_item_status, quantity_in_stock
                FROM product_items WHERE id = %s"""
                cursor.execute(
                    GET_PRICE_AND_QTY_IN_STOCK,
                    (product_item_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    abort(400, "Bad Request")
                if row.product_item_status != "published":
                    app.logger.debug(
                        "product_item_status is not published for %s", product_item_id
                    )
                    abort(400, "Bad Request")
                order_item_dict["original_price"] = row.original_price
                order_item_dict["offer_price"] = row.offer_price
                quantity_in_stock = row.quantity_in_stock
                quantity = order_item_dict.get("quantity")
                if quantity > quantity_in_stock:
                    app.logger.debug(
                        "error: order_item_dict['quantity'] = %s > quantity_in_stock = %s for product_item_id = %s",
                        quantity,
                        quantity_in_stock,
                        product_item_id,
                    )
                    abort(400, "Bad Request")
                remaining_quantity = quantity_in_stock - quantity
                UPDATE_QUANTITY_IN_STOCK = (
                    """UPDATE product_items SET quantity_in_stock = %s WHERE id = %s"""
                )
                cursor.execute(
                    UPDATE_QUANTITY_IN_STOCK,
                    (
                        remaining_quantity,
                        product_item_id,
                    ),
                )
                if cursor.rowcount != 1:
                    abort(400, "Bad Request: update addresses row error")

                order_dict["total_original_price"] += order_item_dict.get(
                    "original_price"
                )
                order_dict["sub_total"] += order_item_dict.get("offer_price")
                order_dict["total_discount"] += order_item_dict.get("discount", 0)
                order_dict["total_tax"] += order_item_dict.get("tax", 0)
            order_dict["grand_total"] = (
                order_dict["sub_total"]
                - order_dict["total_discount"]
                + order_dict["total_tax"]
            )
            # app.logger.debug("order_dict= %s", order_dict)

            # add payment info
            CREATE_PAYMENT = """INSERT INTO payments(provider, provider_order_id, provider_payment_id, 
            payment_mode, payment_status, added_at)
            VALUES(%s, %s, %s, %s, %s, %s) RETURNING id"""

            cursor.execute(
                CREATE_PAYMENT,
                (
                    "POD",
                    0,
                    None,
                    "POD",
                    "initiated",
                    datetime.now(timezone.utc),
                ),
            )
            payment_id = cursor.fetchone()[0]

            address_id = order_dict.get("shipping_address_id")
            GET_ADDRESS = """SELECT a.id AS address_id, a.full_name, a.mobile_no, 
            a.address_line1, a.address_line2, a.city, a.district, a.state,
            a.country, a.pincode, a.landmark, a.added_at, a.updated_at
            FROM addresses a WHERE a.id = %s"""

            cursor.execute(GET_ADDRESS, (address_id,))
            row = cursor.fetchone()
            if not row:
                abort(400, "No such address by id")
            address_dict = {}
            address_dict["address_id"] = row.address_id
            address_dict["full_name"] = row.full_name
            address_dict["mobile_no"] = row.mobile_no
            address_dict["address_line1"] = row.address_line1
            address_dict["address_line2"] = row.address_line2
            address_dict["city"] = row.city
            address_dict["district"] = row.district
            address_dict["state"] = row.state
            address_dict["country"] = row.country
            address_dict["pincode"] = row.pincode
            address_dict["landmark"] = row.landmark
            address_dict.update(
                json.loads(json.dumps({"added_at": row.added_at}, default=str))
            )
            address_dict.update(
                json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
            )

            # add adddress for order
            CREATE_ORDER_ADDRESS = """INSERT INTO order_addresses(full_name, mobile_no, address_line1, address_line2, 
            city, district, state, country, pincode, landmark, added_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

            cursor.execute(
                CREATE_ORDER_ADDRESS,
                (
                    address_dict.get("full_name"),
                    address_dict.get("mobile_no"),
                    address_dict.get("address_line1"),
                    address_dict.get("address_line2"),
                    address_dict.get("city"),
                    address_dict.get("district"),
                    address_dict.get("state"),
                    address_dict.get("country"),
                    address_dict.get("pincode"),
                    address_dict.get("landmark"),
                    current_time,
                ),
            )
            order_address_id = cursor.fetchone()[0]

            CREATE_ORDER = """INSERT INTO orders(customer_id, payment_id, order_address_id, order_status, checkout_from,
            total_original_price, sub_total, total_discount, total_tax, grand_total, added_at)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

            cursor.execute(
                CREATE_ORDER,
                (
                    customer_id,
                    payment_id,
                    order_address_id,
                    "placed",
                    checkout_from,
                    order_dict.get("total_original_price"),
                    order_dict.get("sub_total"),
                    order_dict.get("total_discount"),
                    order_dict.get("total_tax"),
                    order_dict.get("grand_total"),
                    current_time,
                ),
            )
            order_id = cursor.fetchone()[0]

            # add order items
            INSERT_ORDER_ITEMS = """INSERT INTO order_items(order_id, product_item_id, quantity,
            original_price, offer_price, discount_percent, discount, tax, added_at)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)"""

            values_tuple_list = []
            for order_item_dict in order_dict["order_items"]:
                values_tuple = (
                    order_id,
                    order_item_dict.get("product_item_id"),
                    order_item_dict.get("quantity"),
                    order_item_dict.get("original_price"),
                    order_item_dict.get("offer_price"),
                    order_item_dict.get("discount_percent", 0),
                    order_item_dict.get("discount", 0),
                    order_item_dict.get("tax", 0),
                    current_time,
                )
                values_tuple_list.append(values_tuple)
            # app.logger.debug("values_tuple_list= %s", values_tuple_list)

            psycopg2.extras.execute_batch(cursor, INSERT_ORDER_ITEMS, values_tuple_list)

            # remove items from cart if checkout_from is 'cart'
            if checkout_from == "cart":
                for order_item_dict in order_dict["order_items"]:
                    product_item_id = order_item_dict["product_item_id"]
                    quantity = order_item_dict["quantity"]

                    GET_CART_ID = """SELECT id FROM carts WHERE customer_id = %s"""
                    cursor.execute(GET_CART_ID, (customer_id,))
                    row = cursor.fetchone()
                    if not row:
                        app.logger.debug("cart_id not found!")
                    cart_id = row.id

                    DELETE_ITEMS_ORDERED_FROM_CART = """DELETE FROM cart_items WHERE product_item_id = %s AND cart_id = %s"""
                    cursor.execute(
                        DELETE_ITEMS_ORDERED_FROM_CART,
                        (
                            product_item_id,
                            cart_id,
                        ),
                    )
                    # if cursor.rowcount == 0:
                    #     abort(400, "Bad Request: delete cart_items rows error")

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
        return f"order_id = {order_id} created successfully", 201

    @f_jwt.jwt_required()
    def get(self, order_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        GET_ORDER = """SELECT o.id AS order_id, o.customer_id, o.mobile_no,
        o.total_original_price, o.sub_total, o.total_discount, o.total_tax, o.grand_total, o.added_at, o.updated_at,
        ad.id AS address_id, ad.address_line1, ad.address_line2, ad.district, ad.city, ad.state, ad.country, ad.pincode, ad.landmark
        FROM orders o
        JOIN addresses ad ON ad.id = o.shipping_address_id
        WHERE o.id = %s"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_ORDER, (order_id,))
            row = cursor.fetchone()
            if row is None:
                return {}
            order_dict = {}
            order_dict["order_id"] = row.order_id
            order_dict["customer_id"] = row.customer_id
            order_dict["mobile_no"] = row.mobile_no
            order_dict.update(
                json.loads(
                    json.dumps(
                        {"total_original_price": row.total_original_price}, default=str
                    )
                )
            )
            order_dict.update(
                json.loads(json.dumps({"sub_total": row.sub_total}, default=str))
            )
            order_dict.update(
                json.loads(
                    json.dumps({"total_discount": row.total_discount}, default=str)
                )
            )
            order_dict.update(
                json.loads(json.dumps({"total_tax": row.total_tax}, default=str))
            )
            order_dict.update(
                json.loads(json.dumps({"grand_total": row.grand_total}, default=str))
            )
            order_dict.update(
                json.loads(json.dumps({"added_at": row.added_at}, default=str))
            )
            order_dict.update(
                json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
            )

            address_dict = {}
            address_dict["address_id"] = row.address_id
            address_dict["address_line1"] = row.address_line1
            address_dict["address_line2"] = row.address_line2
            address_dict["district"] = row.district
            address_dict["city"] = row.city
            address_dict["state"] = row.state
            address_dict["country"] = row.country
            address_dict["pincode"] = row.pincode
            address_dict["landmark"] = row.landmark
            order_dict.update({"shipping_address": address_dict})

            GET_ORDER_ITEMS = """SELECT oi.id AS order_item_id, oi.order_item_status, oi.quantity, 
            oi.original_price, oi.offer_price, oi.discount_percent, oi.discount, oi.tax, oi.product_item_id, 
            pi.product_id, p.product_name
            FROM order_items oi
            JOIN product_items pi ON pi.id = oi.product_item_id
            JOIN products p ON p.id = pi.product_id
            WHERE oi.order_id = %s"""

            cursor.execute(GET_ORDER_ITEMS, (order_id,))
            rows = cursor.fetchall()
            order_items_list = []
            if not rows:
                return {}
            for row in rows:
                order_item_dict = {}
                order_item_dict["order_item_id"] = row.order_item_id
                order_item_dict["order_item_status"] = row.order_item_status
                order_item_dict["quantity"] = row.quantity
                order_item_dict.update(
                    json.loads(
                        json.dumps({"original_price": row.original_price}, default=str)
                    )
                )
                order_item_dict.update(
                    json.loads(
                        json.dumps({"offer_price": row.offer_price}, default=str)
                    )
                )
                order_item_dict.update(
                    json.loads(
                        json.dumps(
                            {"discount_percent": row.discount_percent}, default=str
                        )
                    )
                )
                order_item_dict.update(
                    json.loads(json.dumps({"discount": row.discount}, default=str))
                )
                order_item_dict.update(
                    json.loads(json.dumps({"tax": row.tax}, default=str))
                )
                order_item_dict["product_item_id"] = row.product_item_id
                order_item_dict["product_id"] = row.product_id
                order_item_dict["product_name"] = row.product_name

                media_dict = {}
                GET_BASE_MEDIA = """SELECT m.id AS media_id, m.name, m.path
                    FROM media m
                    WHERE m.id = (
                        SELECT pim.media_id From product_item_medias pim
                        WHERE pim.product_item_id = %s
                        ORDER BY pim.display_order
                        LIMIT 1
                    )"""
                cursor.execute(
                    GET_BASE_MEDIA, (order_item_dict.get("product_item_id"),)
                )
                row = cursor.fetchone()
                if row is None:
                    app.logger.debug("No media rows")
                    order_item_dict.update({"media": media_dict})
                    order_items_list.append(order_item_dict)
                    continue
                media_dict["id"] = row.media_id
                media_dict["name"] = row.name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
                else:
                    media_dict["path"] = None
                order_item_dict.update({"media": media_dict})
                order_items_list.append(order_item_dict)
            order_dict.update({"order_items": order_items_list})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(order_dict)
        return order_dict


class OrderItems(Resource):
    @f_jwt.jwt_required()
    def patch(self, order_item_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        # app.logger.debug("user_type= %s", user_type)
        data = request.get_json()
        order_item_status = data.get("order_item_status", None)
        if not order_item_status:
            abort(400, "Bad Request")

        if user_type == "seller":
            ALLOWED_ORDER_ITEM_STATUS = {
                "pending",
                "confirmed_by_seller",
                "cancelled_by_seller",
                "dispatched",
                "shipped",
                "return_apporved",
                "failure",
                "success",
            }
            if order_item_status not in ALLOWED_ORDER_ITEM_STATUS:
                app.logger.debug("operation not allowed for seller")
                abort(400, "Bad Request")
        elif user_type == "customer":
            ALLOWED_ORDER_ITEM_STATUS = {
                "delivered",
                "cancelled_by_customer",
                "return_request",
                "returned",
            }
            if order_item_status not in ALLOWED_ORDER_ITEM_STATUS:
                app.logger.debug("operation not allowed for customer")
                abort(400, "Bad Request")

        try:
            cursor = app_globals.get_cursor()
            UPDATE_ORDER_ITEM_STATUS = """UPDATE order_items SET order_item_status= %s, updated_at= %s 
            WHERE id= %s"""
            cursor.execute(
                UPDATE_ORDER_ITEM_STATUS,
                (
                    order_item_status,
                    datetime.now(timezone.utc),
                    order_item_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update orders row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"Order Item Id = {order_item_id} modified."}, 200


class CustomerOrders(Resource):
    @f_jwt.jwt_required()
    def get(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        orders_list = []

        # GET_ORDERS = '''SELECT pi.product_id, pi.id AS product_item_id,
        # (SELECT p.product_name FROM products p WHERE p.id = pi.product_id)
        # FROM product_items pi
        # WHERE pi.id IN (
        #     SELECT oi.product_item_id FROM order_items oi WHERE oi.order_id IN (
        #         SELECT o.id FROM orders o WHERE o.customer_id = %s
        #     )
        # )'''

        # GET_ORDERS='''SELECT o.id, o.order_status, o.added_at, o.updated_at, oi.product_item_id
        #     FROM orders o
        #     JOIN LATERAL
        #     (SELECT oi.product_item_id
        #     FROM order_items oi
        #     WHERE oi.order_id = o.id
        #     ) AS oi ON TRUE
        #     WHERE o.customer_id = %s
        #     ORDER BY o.added_at'''

        # GET_ORDERS = """SELECT o.id AS order_id, o.added_at, o.updated_at,
        #     temp.order_item_id, temp.product_item_id, temp.order_item_status, temp.quantity,
        #     temp.product_id, temp.product_name
        #     FROM orders o
        #     JOIN LATERAL(
        #         SELECT oi.id AS order_item_id, oi.product_item_id, oi.order_item_status, oi.quantity,
        #         p.id AS product_id, p.product_name AS product_name
        #         FROM order_items oi
        #         JOIN products p
        #         ON p.id = (
        #             SELECT pi.product_id
        #             FROM product_items pi
        #             WHERE pi.id = oi.product_item_id
        #         )
        #         WHERE oi.order_id = o.id
        #     ) AS temp ON TRUE
        #     WHERE o.customer_id = %s
        #     ORDER BY o.added_at DESC"""

        GET_ORDERS = """SELECT o.id AS order_id, o.added_at, o.updated_at, 
        oi.id AS order_item_id, oi.order_item_status, oi.quantity, 
        p.id AS product_id, p.product_name, p.product_status,
        s.id AS seller_id, s.seller_name, s.email,
        pi.id AS product_item_id, pi.product_variant_name, pi."SKU", pi.quantity_in_stock, pi.product_item_status
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        JOIN product_items pi ON pi.id = oi.product_item_id
        JOIN products p ON p.id = pi.product_id
        JOIN sellers s ON p.seller_id = s.id 
        WHERE o.customer_id = %s
        ORDER BY o.added_at DESC"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_ORDERS, (customer_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                order_dict = {}
                order_dict["order_id"] = row.order_id
                order_dict.update(
                    json.loads(json.dumps({"added_at": row.added_at}, default=str))
                )
                order_dict.update(
                    json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
                )
                order_dict["order_item_id"] = row.order_item_id
                order_dict["order_item_status"] = row.order_item_status
                order_dict["quantity"] = row.quantity
                order_dict["product_id"] = row.product_id
                order_dict["product_name"] = row.product_name
                order_dict["product_status"] = row.product_status

                seller_dict = {}
                seller_dict["id"] = row.seller_id
                seller_dict["seller_name"] = row.seller_name
                seller_dict["email"] = row.email
                order_dict.update({"seller": seller_dict})

                order_dict["product_item_id"] = row.product_item_id
                order_dict["product_variant_name"] = row.product_variant_name
                order_dict["SKU"] = row.SKU
                order_dict["quantity_in_stock"] = row.quantity_in_stock
                order_dict["product_item_status"] = row.product_item_status

                media_dict = {}
                GET_BASE_MEDIA = """SELECT m.id AS media_id, m.name, m.path
                FROM media m
                WHERE m.id = (
                    SELECT pim.media_id From product_item_medias pim
                    WHERE pim.product_item_id = %s 
                    ORDER BY pim.display_order 
                    LIMIT 1
                )"""
                cursor.execute(GET_BASE_MEDIA, (order_dict.get("product_item_id"),))
                row = cursor.fetchone()
                if row is None:
                    app.logger.debug("No media rows")
                    order_dict.update({"media": media_dict})
                    orders_list.append(order_dict)
                    continue
                media_dict["id"] = row.media_id
                media_dict["name"] = row.name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
                else:
                    media_dict["path"] = None
                order_dict.update({"media": media_dict})
                orders_list.append(order_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(orders_list)
        return orders_list
