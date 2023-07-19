from datetime import datetime, timezone
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


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

        data = {
            "amount": 500,
            "currency": "INR",
            "receipt": "order_rcptid_11",
            "payment_capture": 1,
        }

        payment_order = app_globals.payment_client.order.create(data=data)
        app.logger.debug("payment_order=", payment_order)
        if not payment_order:
            abort(400, "Bad request")

        return payment_order, 201
