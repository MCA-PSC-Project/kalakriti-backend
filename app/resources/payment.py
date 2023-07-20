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
        # if user_type != "customer":
        #     abort(403, "Forbidden: only customers can create orders")
        data = request.get_json()
        checkout_dict = json.loads(json.dumps(data))
        current_time = datetime.now(timezone.utc)
        checkout_dict["total_original_price"] = 0
        checkout_dict["sub_total"] = 0
        checkout_dict["total_discount"] = 0
        checkout_dict["total_tax"] = 0

        try:
            for checkout_item_dict in checkout_dict["order_items"]:
                product_item_id = checkout_item_dict.get("product_item_id")
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
                checkout_item_dict["original_price"] = row.original_price
                checkout_item_dict["offer_price"] = row.offer_price
                quantity_in_stock = row.quantity_in_stock
                quantity = checkout_item_dict.get("quantity")
                if quantity > quantity_in_stock:
                    app.logger.debug(
                        "error: checkout_item_dict['quantity'] = %s > quantity_in_stock = %s for product_item_id = %s",
                        quantity,
                        quantity_in_stock,
                        product_item_id,
                    )
                    abort(400, "Bad Request")
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
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()

        data = {
            "amount": int(checkout_dict["grand_total"] * 100),
            "currency": "INR",
            "receipt": "order_rcptid_11",
            "payment_capture": 1,
        }

        payment_order = app_globals.payment_client.order.create(data=data)
        app.logger.debug("payment_order=", payment_order)
        if not payment_order:
            abort(400, "Bad request")

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
            # YOU CAN SAVE THE DETAILS IN YOUR DATABASE IF YOU WANT

            return {
                "msg": "success",
                "orderId": razorpayOrderId,
                "paymentId": razorpayPaymentId,
            }, 200
        except Exception as error:
            return str(error), 500
