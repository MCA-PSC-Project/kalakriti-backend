from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Orders(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        # claims = f_jwt.get_jwt()
        # user_type = claims['user_type']
        # app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        order_dict = json.loads(json.dumps(data))
        current_time = datetime.now()

        order_dict['total_original_price'] = 0
        order_dict['sub_total'] = 0
        order_dict['total_discount'] = 0
        order_dict['total_tax'] = 0
        for order_item_dict in order_dict['order_items']:
            order_dict['total_original_price'] += order_item_dict.get(
                'original_price')
            order_dict['sub_total'] += order_item_dict.get('offer_price')
            order_dict['total_discount'] += order_item_dict.get('discount')
            order_dict['total_tax'] += order_item_dict.get('tax')
        order_dict['grand_total'] = (
            order_dict['sub_total'] -
            order_dict['total_discount'] + order_dict['total_tax']
        )
        app.logger.debug("order_dict= %s", order_dict)

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        # print(app_globals.db_conn)
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            CREATE_ORDER = '''INSERT INTO orders(user_id, shipping_address_id, phone,
            total_original_price, sub_total, total_discount, total_tax, grand_total, added_at)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id'''

            cursor.execute(CREATE_ORDER,
                           (user_id, order_dict.get('shipping_address_id'), order_dict.get('phone'),
                            order_dict.get('total_original_price'),
                            order_dict.get('sub_total'), order_dict.get(
                                'total_discount'),
                            order_dict.get('total_tax'), order_dict.get(
                                'grand_total'),
                            current_time,))
            order_id = cursor.fetchone()[0]

            # add order items
            INSERT_ORDER_ITEMS = '''INSERT INTO order_items(order_id, product_item_id, quantity,
            original_price, offer_price, discount_percent, discount, tax)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s)'''

            values_tuple_list = []
            for order_item_dict in order_dict['order_items']:
                values_tuple = (
                    order_id, order_item_dict.get(
                        "product_item_id"), order_item_dict.get("quantity"),
                    order_item_dict.get(
                        "original_price"), order_item_dict.get("offer_price"),
                    order_item_dict.get("discount_percent"), order_item_dict.get(
                        "discount"), order_item_dict.get("tax")
                )
                values_tuple_list.append(values_tuple)
            app.logger.debug("values_tuple_list= %s", values_tuple_list)

            psycopg2.extras.execute_batch(
                cursor, INSERT_ORDER_ITEMS, values_tuple_list)

            # add payment info
            # INSERT_PAYMENT_INFO = '''INSERT INTO payments
            # (order_id, provider, provider_order_id, provider_payment_id, payment_mode, payment_status, added_at)
            # VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id'''

            # cursor.execute(INSERT_PAYMENT_INFO,
            #                (order_id, current_time,))
            # payment_id = cursor.fetchone()[0]

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
        return f"order_id = {order_id} created successfully", 201

    @f_jwt.jwt_required()
    def get(self, order_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)

        GET_ORDER = '''SELECT o.id AS order_id, o.user_id, o.phone, o.order_status,
        o.total_original_price, o.sub_total, o.total_discount, o.total_tax, o.grand_total, o.added_at, o.updated_at,
        ad.id AS address_id, ad.address, ad.district, ad.city, ad.state, ad.country, ad.pincode, ad.landmark
        FROM orders o
        JOIN addresses ad ON ad.id = o.shipping_address_id
        WHERE o.id = %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)
            cursor.execute(GET_ORDER, (order_id,))
            row = cursor.fetchone()
            if row is None:
                return {}
            
            order_dict = {}
            order_dict['order_id'] = row.order_id
            order_dict['user_id'] = row.user_id
            order_dict['phone'] = row.phone
            order_dict['order_status'] = row.order_status
            order_dict.update(json.loads(
                json.dumps({'total_original_price': row.total_original_price}, default=str)))
            order_dict.update(json.loads(
                json.dumps({'sub_total': row.sub_total}, default=str)))
            order_dict.update(json.loads(
                json.dumps({'total_discount': row.total_discount}, default=str)))
            order_dict.update(json.loads(
                json.dumps({'total_tax': row.total_tax}, default=str)))
            order_dict.update(json.loads(
                json.dumps({'grand_total': row.grand_total}, default=str)))
            order_dict.update(json.loads(
                json.dumps({'added_at': row.added_at}, default=str)))
            order_dict.update(json.loads(
                json.dumps({'updated_at': row.updated_at}, default=str)))

            address_dict = {}
            address_dict['address_id'] = row.address_id
            address_dict['address'] = row.address
            address_dict['district'] = row.district
            address_dict['city'] = row.city
            address_dict['state'] = row.state
            address_dict['country'] = row.country
            address_dict['pincode'] = row.pincode
            address_dict['landmark'] = row.landmark
            order_dict.update({"shipping_address": address_dict})

            GET_ORDER_ITEMS = '''SELECT oi.id AS order_item_id, oi.quantity, oi.original_price, oi.offer_price, 
            oi.discount_percent, oi.discount, oi.tax, oi.product_item_id, 
            pi.product_id, p.product_name
            FROM order_items oi
            JOIN product_items pi ON pi.id = oi.product_item_id
            JOIN products p ON p.id = pi.product_id
            WHERE oi.order_id = %s'''

            cursor.execute(GET_ORDER_ITEMS, (order_id,))
            rows = cursor.fetchall()
            order_items_list=[]
            if not rows:
                return {}
            for row in rows:
                order_item_dict = {}
                order_item_dict['order_item_id'] = row.order_item_id
                order_item_dict['quantity'] = row.quantity
                order_item_dict.update(json.loads(
                    json.dumps({'original_price': row.original_price}, default=str)))
                order_item_dict.update(json.loads(
                    json.dumps({'offer_price': row.offer_price}, default=str)))
                order_item_dict.update(json.loads(
                    json.dumps({'discount_percent': row.discount_percent}, default=str)))
                order_item_dict.update(json.loads(
                    json.dumps({'discount': row.discount}, default=str)))
                order_item_dict.update(json.loads(
                    json.dumps({'tax': row.tax}, default=str)))
                order_item_dict['product_item_id'] = row.product_item_id
                order_item_dict['product_id'] = row.product_id
                order_item_dict['product_name'] = row.product_name

                media_dict = {}
                GET_BASE_MEDIA = '''SELECT m.id AS media_id, m.name, m.path
                    FROM media m
                    WHERE m.id = (
                        SELECT pim.media_id From product_item_medias pim
                        WHERE pim.product_item_id = %s
                        ORDER BY pim.display_order
                        LIMIT 1
                    )
                    '''
                cursor.execute(
                    GET_BASE_MEDIA, (order_item_dict.get('product_item_id'),))
                row = cursor.fetchone()
                if row is None:
                        app.logger.debug("No media rows")
                        order_item_dict.update({"media": media_dict})
                        order_items_list.append(order_item_dict)
                        continue
                media_dict['id'] = row.media_id
                media_dict['name'] = row.name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    media_dict['path'] = None
                order_item_dict.update({"media": media_dict})
                order_items_list.append(order_item_dict)
            order_dict.update({"order_items": order_items_list})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(order_dict)
        return order_dict

    @f_jwt.jwt_required()
    def patch(self, order_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        order_status = data.get("order_status", None)
        if not order_status:
            abort(400, 'Bad Request')
        current_time = datetime.now()

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            UPDATE_ORDER_STATUS = '''UPDATE orders SET order_status= %s, updated_at= %s WHERE id= %s'''

            cursor.execute(
                UPDATE_ORDER_STATUS, (order_status, current_time, order_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update orders row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"Order id = {order_id} modified."}, 200


class UserOrders(Resource):
    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)

        orders_list = []

        # GET_ORDERS = '''SELECT pi.product_id, pi.id AS product_item_id,
        # (SELECT p.product_name FROM products p WHERE p.id = pi.product_id)
        # FROM product_items pi
        # WHERE pi.id IN (
        #     SELECT oi.product_item_id FROM order_items oi WHERE oi.order_id IN (
        #         SELECT o.id FROM orders o WHERE o.user_id = %s
        #     )
        # )'''

        # GET_ORDERS='''SELECT o.id, o.order_status, o.added_at, o.updated_at, oi.product_item_id
        #     FROM orders o
        #     JOIN LATERAL
        #     (SELECT oi.product_item_id
        #     FROM order_items oi
        #     WHERE oi.order_id = o.id
        #     ) AS oi ON TRUE
        #     WHERE o.user_id = %s
        #     ORDER BY o.added_at'''

        GET_ORDERS = '''SELECT o.id AS order_id, o.order_status, o.added_at, o.updated_at, 
            temp.order_item_id, temp.product_item_id, temp.quantity, temp.product_id, temp.product_name 
            FROM orders o 
            JOIN LATERAL(
                SELECT oi.id AS order_item_id, oi.product_item_id, oi.quantity, 
                p.id AS product_id, p.product_name AS product_name
                FROM order_items oi 
                JOIN products p
                ON p.id = (
                    SELECT pi.product_id 
                    FROM product_items pi
                    WHERE pi.id = oi.product_item_id
                ) 
                WHERE oi.order_id = o.id
            ) AS temp ON TRUE
            WHERE o.user_id = %s
            ORDER BY o.added_at DESC'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)
            cursor.execute(GET_ORDERS, (user_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                order_dict = {}
                order_dict['order_id'] = row.order_id
                order_dict['order_status'] = row.order_status
                order_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                order_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))
                order_dict['order_item_id'] = row.order_item_id
                order_dict['product_item_id'] = row.product_item_id
                order_dict['quantity'] = row.quantity
                order_dict['product_id'] = row.product_id
                order_dict['product_name'] = row.product_name

                media_dict = {}
                GET_BASE_MEDIA = '''SELECT m.id AS media_id, m.name, m.path
                FROM media m
                WHERE m.id = (
                    SELECT pim.media_id From product_item_medias pim
                    WHERE pim.product_item_id = %s 
                    ORDER BY pim.display_order 
                    LIMIT 1
                ) 
                '''
                cursor.execute(
                    GET_BASE_MEDIA, (order_dict.get('product_item_id'),))
                row = cursor.fetchone()
                if row is None:
                    app.logger.debug("No media rows")
                    order_dict.update({"media": media_dict})
                    orders_list.append(order_dict)
                    continue
                media_dict['id'] = row.media_id
                media_dict['name'] = row.name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    media_dict['path'] = None
                order_dict.update({"media": media_dict})
                orders_list.append(order_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(orders_list)
        return orders_list
