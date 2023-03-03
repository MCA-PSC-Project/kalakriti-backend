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
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

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

            CREATE_ORDER = '''INSERT INTO orders(user_id, shipping_address, city, district, state, country, pincode,
            phone, total_original_price, sub_total, total_discount, total_tax, grand_total, ordered_at) 
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id'''

            cursor.execute(CREATE_ORDER,
                           (user_id, order_dict.get('address'),
                            order_dict.get('city'), order_dict.get('district'),
                            order_dict.get('state'), order_dict.get('country'),
                            order_dict.get('pincode'), order_dict.get('phone'),
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
