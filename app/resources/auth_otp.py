from datetime import datetime, timezone, timedelta
from flask_restful import Resource
from flask import abort, current_app as app, request
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import app.otp as otp


class GetMobileOtp(Resource):
    def post(self):
        data = request.get_json()
        mobile_no = data.get("mobile_no", None)
        if not mobile_no:
            abort(400, "Bad Request")

        generated_motp = otp.generate_motp()
        app.logger.debug("generated otp= %s", generated_motp)
        now_plus_10_mins = datetime.now(timezone.utc) + timedelta(minutes=10)

        UPSERT_MOBILE_OTP = """INSERT INTO mobile_otp(mobile_no, motp, expiry_at)
        VALUES(%s, %s, %s)
        ON CONFLICT (mobile_no)
        DO UPDATE SET motp = %s, expiry_at = %s"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPSERT_MOBILE_OTP,
                (
                    mobile_no,
                    generated_motp,
                    now_plus_10_mins,
                    generated_motp,
                    now_plus_10_mins,
                ),
            )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()

        if app.config["SEND_MOTP"]:
            # TODO: Add code to send motp here
            pass
        return "Otp has been sent successfully", 200


class MobileOtpLoginCustomer(Resource):
    def post(self):
        data = request.get_json()
        provided_mobile_no = data.get("mobile_no", None)
        provided_motp = data.get("motp", None)

        if not provided_mobile_no or not provided_motp:
            app.logger.debug("Both mobile_no and motp must be provided")
            abort(400, "Bad Request")

        # check if user of given mobile already exists or not
        GET_CUSTOMER = "SELECT id FROM customers WHERE mobile_no= %s"
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_CUSTOMER, (provided_mobile_no,))
            row = cursor.fetchone()
            if row is None:
                app.logger.debug("No customer with given mobile found.")
                abort(400, "Bad Request: User not found")
            else:
                customer_id = row.id
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()

        GET_MOTP_AND_EXPIRY = (
            """SELECT motp, expiry_at FROM mobile_otp WHERE mobile_no= %s"""
        )
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_MOTP_AND_EXPIRY, (provided_mobile_no,))
            row = cursor.fetchone()
            if row is None:
                app.logger.debug("No such mobile no in mobile_otp table")
                abort(400, "Bad Request")
            stored_motp = row.motp
            expiry_at = row.expiry_at
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()

        if provided_motp != stored_motp or datetime.now(expiry_at.tzinfo) > expiry_at:
            abort(400, "Bad Request")

        user_type = "customer"
        access_token = f_jwt.create_access_token(
            identity=customer_id, additional_claims={"user_type": user_type}, fresh=True
        )
        refresh_token = f_jwt.create_refresh_token(
            identity=customer_id, additional_claims={"user_type": user_type}
        )
        return {"access_token": access_token, "refresh_token": refresh_token}, 202


class MobileOtpLoginSeller(Resource):
    def post(self):
        data = request.get_json()
        provided_mobile_no = data.get("mobile_no", None)
        provided_motp = data.get("motp", None)

        if not provided_mobile_no or not provided_motp:
            app.logger.debug("Both mobile_no and motp must be provided")
            abort(400, "Bad Request")

        # check if user of given mobile already exists or not
        GET_SELLER = "SELECT id FROM sellers WHERE mobile_no= %s"
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_SELLER, (provided_mobile_no,))
            row = cursor.fetchone()
            if row is None:
                app.logger.debug("No seller with given mobile found.")
                abort(400, "Bad Request: User not found")
            else:
                seller_id = row.id
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()

        GET_MOTP_AND_EXPIRY = (
            """SELECT motp, expiry_at FROM mobile_otp WHERE mobile_no= %s"""
        )
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_MOTP_AND_EXPIRY, (provided_mobile_no,))
            row = cursor.fetchone()
            if row is None:
                app.logger.debug("No such mobile no in mobile_otp table")
                abort(400, "Bad Request")
            stored_motp = row.motp
            expiry_at = row.expiry_at
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()

        if provided_motp != stored_motp or datetime.now(expiry_at.tzinfo) > expiry_at:
            abort(400, "Bad Request")

        user_type = "seller"
        access_token = f_jwt.create_access_token(
            identity=seller_id, additional_claims={"user_type": user_type}, fresh=True
        )
        refresh_token = f_jwt.create_refresh_token(
            identity=seller_id, additional_claims={"user_type": user_type}
        )
        return {"access_token": access_token, "refresh_token": refresh_token}, 202


class MobileOtpLoginAdmin(Resource):
    def post(self):
        data = request.get_json()
        provided_mobile_no = data.get("mobile_no", None)
        provided_motp = data.get("motp", None)

        if not provided_mobile_no or not provided_motp:
            app.logger.debug("Both mobile_no and motp must be provided")
            abort(400, "Bad Request")

        # check if user of given mobile already exists or not
        GET_CUSTOMER = "SELECT id, is_super_admin FROM admins WHERE mobile_no= %s"
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_CUSTOMER, (provided_mobile_no,))
            row = cursor.fetchone()
            if row is None:
                app.logger.debug("No admin with given mobile found.")
                abort(400, "Bad Request: User not found")
            else:
                admin_id = row.id
                is_super_admin = row.is_super_admin
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()

        GET_MOTP_AND_EXPIRY = (
            """SELECT motp, expiry_at FROM mobile_otp WHERE mobile_no= %s"""
        )
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_MOTP_AND_EXPIRY, (provided_mobile_no,))
            row = cursor.fetchone()
            if row is None:
                app.logger.debug("No such mobile no in mobile_otp table")
                abort(400, "Bad Request")
            stored_motp = row.motp
            expiry_at = row.expiry_at
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()

        if provided_motp != stored_motp or datetime.now(expiry_at.tzinfo) > expiry_at:
            abort(400, "Bad Request")

        if is_super_admin:
            user_type = "super_admin"
        else:
            user_type = "admin"
        access_token = f_jwt.create_access_token(
            identity=admin_id, additional_claims={"user_type": user_type}, fresh=True
        )
        refresh_token = f_jwt.create_refresh_token(
            identity=admin_id, additional_claims={"user_type": user_type}
        )
        return {"access_token": access_token, "refresh_token": refresh_token}, 202
