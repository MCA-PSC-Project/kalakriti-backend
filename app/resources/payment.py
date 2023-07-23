from datetime import datetime, timezone
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app
import hmac
import hashlib


class Payment(Resource):
    @f_jwt.jwt_required()
    def post(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        # app.logger.debug("user_type= %s", user_type)
        if user_type != "customer":
            abort(403, "Forbidden: only customers can create orders")

        current_time = datetime.now(timezone.utc)
        data = request.get_json()
        checkout_dict = json.loads(json.dumps(data))
        shipping_address_id = checkout_dict.get("shipping_address_id")
        if not shipping_address_id:
            abort(404, "shipping_address_id not provided")

        checkout_dict["total_original_price"] = 0
        checkout_dict["sub_total"] = 0
        checkout_dict["total_discount"] = 0
        checkout_dict["total_tax"] = 0

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        try:
            checkout_from_cart = checkout_dict.get("checkout_from_cart")
            if checkout_from_cart == False:
                # buy now
                checkout_item_dict = checkout_dict.get("checkout_item")
                if not checkout_item_dict:
                    abort(404, "checkout_item not provided")

                product_item_id = checkout_item_dict.get("product_item_id")
                quantity = checkout_item_dict.get("quantity")
            
                    cursor = app_globals.get_named_tuple_cursor()
                    GET_PRICE_AND_QTY_IN_STOCK = """SELECT original_price, offer_price, product_item_status, quantity_in_stock
                    FROM product_items WHERE id = %s"""
                    cursor.execute(
                        GET_PRICE_AND_QTY_IN_STOCK,
                        (product_item_id,),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        abort(400, "Bad Request: product item not found")
                    if row.product_item_status != "published":
                        app.logger.debug(
                            "product_item_status is not published for %s", product_item_id
                        )
                        abort(400, "Bad Request")
                    checkout_item_dict["original_price"] = row.original_price
                    checkout_item_dict["offer_price"] = row.offer_price
                    quantity_in_stock = row.quantity_in_stock
                    if quantity > quantity_in_stock:
                        app.logger.debug(
                            "error: order_item_dict['quantity'] = %s > quantity_in_stock = %s for product_item_id = %s",
                            quantity,
                            quantity_in_stock,
                            product_item_id,
                        )
                        abort(400, "Bad Request")
                    # remaining_quantity = quantity_in_stock - quantity
                    # UPDATE_QUANTITY_IN_STOCK = (
                    #     """UPDATE product_items SET quantity_in_stock = %s WHERE id = %s"""
                    # )
                    # cursor.execute(
                    #     UPDATE_QUANTITY_IN_STOCK,
                    #     (
                    #         remaining_quantity,
                    #         product_item_id,
                    #     ),
                    # )
                    # if cursor.rowcount != 1:
                    #     abort(400, "Bad Request: update product_items row error")

                    checkout_dict["total_original_price"] += checkout_item_dict.get(
                        "original_price"
                    )
                    checkout_dict["sub_total"] += checkout_item_dict.get(
                        "offer_price"
                    ) * checkout_item_dict.get("quantity")
                    checkout_dict["total_discount"] += checkout_item_dict.get("discount")
                    checkout_dict["total_tax"] += checkout_item_dict.get("tax")
                    checkout_dict["grand_total"] = (
                        checkout_dict["sub_total"]
                        - checkout_dict["total_discount"]
                        + checkout_dict["total_tax"]
                    )
                    # app.logger.debug("order_dict= %s", order_dict)
                    app.logger.debug("grand_total= %s", checkout_dict.get("grand_total"))
                
            elif checkout_from_cart == True:
                pass
            else:
                abort(404, "checkout_from_cart not provided correctly")

            # add payment info
            data = {
                "amount": int(checkout_dict.get("grand_total") * 100),
                "currency": "INR",
                "receipt": "order_rcptid_11",
                "payment_capture": 1,
            }

            payment_order = app_globals.payment_client.order.create(data=data)
            # app.logger.debug("payment_client= %s", app_globals.payment_client)
            # app.logger.debug("payment_order= %s", payment_order)
            if not payment_order:
                app.logger.debug("error : payment_order= %s", payment_order)
                abort(400, "Bad request")

            CREATE_PAYMENT = """INSERT INTO payments(provider, provider_order_id, provider_payment_id, 
            payment_mode, payment_status, added_at)
            VALUES(%s, %s, %s, %s, %s, %s) RETURNING id"""

            cursor.execute(
                CREATE_PAYMENT,
                (
                    app.config["PAYMENT_PROVIDER"],
                    payment_order.get("id"),
                    None,
                    None,
                    "initiated",
                    datetime.now(timezone.utc),
                ),
            )
            payment_id = cursor.fetchone()[0]

            # CREATE_ORDER = """INSERT INTO orders(customer_id, payment_id, order_status, total_original_price, sub_total,
            # total_discount, total_tax, grand_total, added_at)
            # VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

            # cursor.execute(
            #     CREATE_ORDER,
            #     (
            #         customer_id,
            #         payment_id,
            #         "checkout",
            #         checkout_dict.get("total_original_price"),
            #         checkout_dict.get("sub_total"),
            #         checkout_dict.get("total_discount"),
            #         checkout_dict.get("total_tax"),
            #         checkout_dict.get("grand_total"),
            #         current_time,
            #     ),
            # )
            # order_id = cursor.fetchone()[0]

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
            CREATE_ORDER_ADDRESS = """INSERT INTO order_addresses(order_id, full_name, mobile_no, address_line1, address_line2, 
            city, district, state, country, pincode, landmark, added_at)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

            cursor.execute(
                CREATE_ORDER_ADDRESS,
                (
                    order_id,
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

            # add order items
            INSERT_ORDER_ITEMS = """INSERT INTO order_items(order_id, product_item_id, quantity,
            original_price, offer_price, discount_percent, discount, tax, added_at)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)"""

            values_tuple_list = []
            for checkout_item_dict in checkout_dict["order_items"]:
                values_tuple = (
                    order_id,
                    checkout_item_dict.get("product_item_id"),
                    checkout_item_dict.get("quantity"),
                    checkout_item_dict.get("original_price"),
                    checkout_item_dict.get("offer_price"),
                    checkout_item_dict.get("discount_percent"),
                    checkout_item_dict.get("discount"),
                    checkout_item_dict.get("tax"),
                    current_time,
                )
                values_tuple_list.append(values_tuple)
            app.logger.debug("values_tuple_list= %s", values_tuple_list)

            psycopg2.extras.execute_batch(cursor, INSERT_ORDER_ITEMS, values_tuple_list)
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
        # return f"order_id = {order_id} created successfully", 201
        return payment_order, 201


class PaymentSuccessful(Resource):
    @f_jwt.jwt_required()
    def post(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]

        data = request.get_json()
        razorpay_dict = json.loads(json.dumps(data))
        try:
            # getting the details back from our front-end
            orderCreationId = razorpay_dict["orderCreationId"]
            razorpayPaymentId = razorpay_dict["razorpayPaymentId"]
            razorpayOrderId = razorpay_dict["razorpayOrderId"]
            razorpaySignature = razorpay_dict["razorpaySignature"]

            # Creating our own digest
            # The format should be like this:
            # digest = hmac_sha256(orderCreationId + "|" + razorpayPaymentId, secret);
            key = app.config["PAYMENT_SECRET_KEY"]
            message = f"{orderCreationId}|{razorpayPaymentId}"
            calculated_digest = hmac.new(
                key.encode("utf-8"),
                msg=message.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()

            app.logger.debug("calculated_digest= %s", calculated_digest)
            app.logger.debug("razorpaySignature= %s", razorpaySignature)

            # comparing our digest with the actual signature
            if calculated_digest != razorpaySignature:
                return {"msg": "Transaction not legit!"}, 400

            # THE PAYMENT IS LEGIT & VERIFIED
            # SAVE THE DETAILS IN DATABASE

            # before beginning transaction autocommit must be off
            app_globals.db_conn.autocommit = False
            try:
                cursor = app_globals.get_named_tuple_cursor()
                UPDATE_PAYMENT = """UPDATE payments SET payment_status= %s, provider_payment_id= %s, updated_at= %s 
                WHERE provider_order_id = %s RETURNING id"""

                cursor.execute(
                    UPDATE_PAYMENT,
                    (
                        "success",
                        razorpay_dict.get("razorpayPaymentId"),
                        datetime.now(timezone.utc),
                        razorpay_dict.get("razorpayOrderId"),
                    ),
                )
                if cursor.rowcount != 1:
                    abort(400, "Bad Request: update payments row error")
                payment_id = cursor.fetchone().id
                app.logger.debug("payment_id= %s", payment_id)

                UPDATE_ORDER_STATUS = """UPDATE orders SET order_status= %s, updated_at= %s 
                WHERE payment_id = %s"""

                cursor.execute(
                    UPDATE_ORDER_STATUS,
                    (
                        "placed",
                        datetime.now(timezone.utc),
                        payment_id,
                    ),
                )
                if cursor.rowcount != 1:
                    abort(400, "Bad Request: update orders row error")
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
            return {
                "msg": "success",
                "orderId": razorpayOrderId,
                "paymentId": razorpayPaymentId,
            }, 200
        except Exception as error:
            app.logger.debug(error)
            return str(error), 500
