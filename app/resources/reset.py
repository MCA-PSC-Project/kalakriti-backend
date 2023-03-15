from datetime import datetime
import bcrypt
from flask import Response, make_response, request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
from flask import current_app as app
from app.email_token import generate_email_token, verify_email_token
from flask import flash, redirect, render_template, request, abort, jsonify, url_for

from app.mail import send_email


class RequestResetEmail(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        email = data.get('email', None)

        if not email:
            app.logger.debug("email must be provided")
            abort(400, 'Bad Request')

        # generate email token to send in email
        generated_email_token = generate_email_token(email)
        app.logger.debug("Generated email token= %s",
                         generated_email_token)

        # send email
        reset_email_url = url_for(
            "resetemail", token=generated_email_token, user_id=user_id, user_type=user_type, _external=True)
        app.logger.debug("reset_email_url= %s", reset_email_url)
        reset_email_html_page = render_template(
            "reset_email.html", reset_email_url=reset_email_url)

        subject = "Reset Email"
        app.logger.debug(
            "app.config['SEND_EMAIL']= %s", app.config['SEND_EMAIL'])
        if app.config['SEND_EMAIL']:
            send_email(email, subject, reset_email_html_page)
        app.logger.debug("Email sent successfully!")
        return f"Link to reset email sent to {email} successfully!", 201


class ResetEmail(Resource):
    def get(self):
        args = request.args  # retrieve args from query string
        user_id = args.get('user_id', None)
        user_type = args.get('user_type', None)
        token = args.get('token', None)
        app.logger.debug("?user_type=%s", user_type)
        app.logger.debug("?token=%s", token)
        if not (user_id and user_type and token):
            abort(400, 'Bad Request')
        if user_type not in ['customer', 'seller', 'admin', 'super_admin']:
            abort(400, 'Bad Request')

        try:
            email = verify_email_token(token)
        except:
            flash('The verification link is invalid or has expired.', 'danger')
        if not email:
            app.logger.debug("invalid token")
            abort(400, 'Bad Request')

        if user_type == 'super_admin':
            user_type = 'admin'
        UPDATE_USER_EMAIL = '''UPDATE {} SET email= %s, updated_at= %s WHERE id= %s'''.format(
            user_type+'s')

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(UPDATE_USER_EMAIL, (email, datetime.now(), user_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # return {"message": f"user with id {user_id}, email modified."}, 200
        headers = {'Content-Type': 'text/html'}
        return make_response('Email changed successfully')


class ResetMobile(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        provided_mobile_no = data.get('mobile_no', None)
        provided_motp = data.get("motp", None)

        if not provided_mobile_no or not provided_motp:
            app.logger.debug("Both mobile_no and motp must be provided")
            abort(400, 'Bad Request')

        GET_MOTP_AND_EXPIRY = '''SELECT motp, expiry_at FROM mobile_otp WHERE mobile_no= %s'''
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_MOTP_AND_EXPIRY, (provided_mobile_no,))
            row = cursor.fetchone()
            if row is None:
                app.logger.debug("No such mobile no in mobile_otp table")
                abort(400, 'Bad Request')
            stored_motp = row.motp
            expiry_at = row.expiry_at
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        if provided_motp != stored_motp or datetime.now(expiry_at.tzinfo) > expiry_at:
            abort(400, 'Bad Request')

        if user_type == 'super_admin':
            user_type = 'admin'
        table_name = user_type+'s'
        UPDATE_MOBILE_NUMBER = '''UPDATE {} SET mobile_no= %s, updated_at= %s WHERE id= %s'''.format(
            table_name)
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(UPDATE_MOBILE_NUMBER,
                           (provided_mobile_no, datetime.now(), user_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"mobile_no updated successfully."}, 200


class RequestResetPassword(Resource):
    def post(self):
        data = request.get_json()
        user_type = data.get('user_type', None)
        email = data.get('email', None)
        if not user_type or not email:
            app.logger.debug("Both user_type and email must be provided")
            abort(400, 'Bad Request')

        if user_type == 'super_admin':
            user_type = 'admin'
        table_name = user_type + 's'
        GET_MOTP_AND_EXPIRY = '''SELECT id FROM {} WHERE email= %s'''.format(
            table_name)
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_MOTP_AND_EXPIRY, (email,))
            row = cursor.fetchone()
            if row is None:
                app.logger.debug(
                    "No such email exists in {} table".format(table_name))
                abort(400, 'Bad Request')
            id = row.id
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        # if user with given email exists
        # generate email token to send in email
        generated_email_token = generate_email_token(email)
        app.logger.debug("Generated email token= %s",
                         generated_email_token)

        # send email
        reset_password_url = url_for(
            "resetpassword", _external=True)
        app.logger.debug("reset_password_url= %s", reset_password_url)
        reset_password_html_page = render_template(
            "reset_password_url.html", reset_password_url=reset_password_url, token=generated_email_token,
            user_type=user_type)

        subject = "Reset Password"
        app.logger.debug(
            "app.config['SEND_EMAIL']= %s", app.config['SEND_EMAIL'])
        if app.config['SEND_EMAIL']:
            send_email(email, subject, reset_password_html_page)
        app.logger.debug("Email sent successfully!")
        return f"Link to reset password sent to {email} successfully!", 201


class ResetPassword(Resource):
    def get(self):
        args = request.args  # retrieve args from query string
        user_type = args.get('user_type', None)
        token = args.get('token', None)
        app.logger.debug("?user_type=%s", user_type)
        app.logger.debug("?token=%s", token)
        headers = {'Content-Type': 'text/html'}

        try:
            email = verify_email_token(token)
        except:
            app.logger.debug("invalid email token")
            flash('The link is invalid or has expired.', 'danger')
        if not email:
            app.logger.debug("invalid token")
            abort(400, 'Bad Request')

        reset_password_url = url_for(
            "resetpassword", _external=True)
        app.logger.debug("reset_password_url= %s", reset_password_url)
        return make_response(render_template(
            "reset_password.html", reset_password_url=reset_password_url, token=token,
            user_type=user_type))

    def post(self):
        token = request.form.get('token', None)
        user_type = request.form.get('user_type', None)
        new_password = request.form.get('password', None)
        if not token or not user_type or not new_password:
            abort(400, 'Bad Request')

        try:
            email = verify_email_token(token)
        except:
            app.logger.debug("invalid email token")
            flash('The link is invalid or has expired.', 'danger')
        if not email:
            app.logger.debug("invalid token")
            abort(400, 'Bad Request')

        new_hashed_password = bcrypt.hashpw(
            new_password.encode('utf-8'), bcrypt.gensalt())
        new_hashed_password = new_hashed_password.decode('utf-8')

        CHANGE_USER_PASSWORD = '''UPDATE {} SET hashed_password= %s, updated_at= %s WHERE email= %s'''.format(
            user_type+'s')

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(CHANGE_USER_PASSWORD,
                           (new_hashed_password, datetime.now(), email,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # return {"message": "Status accepted"}, 202
        headers = {'Content-Type': 'text/html'}
        return make_response('Password changed successfully')
