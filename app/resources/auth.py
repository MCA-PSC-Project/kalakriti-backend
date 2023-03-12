from datetime import datetime, timedelta, timezone
from flask import flash, redirect, render_template, request, abort, jsonify, url_for
from flask_restful import Resource
import flask_jwt_extended as f_jwt
import psycopg2
import app.app_globals as app_globals
import bcrypt
from flask import current_app as app
from app.email_token import generate_email_token, verify_email_token
from app.mail import send_email


class RegisterCustomer(Resource):
    def post(self):
        data = request.get_json()
        first_name = data.get("first_name", None)
        last_name = data.get("last_name", None)
        email = data.get("email", None)
        password = data.get("password", None)
        dob = data.get("dob", None)
        gender = data.get("gender", None)

        if not email or not password:
            abort(400, 'Bad Request')
        # check if customer of given email already exists
        CHECK_EMAIL = 'SELECT id FROM customers WHERE email= %s'
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(CHECK_EMAIL, (email,))
            row = cursor.fetchone()
            if row is not None:
                abort(400, 'Bad Request')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        # user doesn't exists..now create user with hashed password
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt())
        hashed_password = hashed_password.decode('utf-8')

        REGISTER_CUSTOMER = '''INSERT INTO customers(first_name, last_name, email, hashed_password, 
        dob, gender, added_at)
        VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id'''

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(REGISTER_CUSTOMER, (first_name, last_name,
                           email, hashed_password, dob, gender, datetime.now(),))
            customer_id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        app.logger.debug(
            "customer with id %s and type = customer created successfully", customer_id)

        # generate token for sending in email for email verification
        generated_email_token = generate_email_token(email)
        app.logger.debug("Generated email token= %s", generated_email_token)

        # send email
        # verify_url = url_for("accounts.verify_email", token=generate_email_token, _external=True)
        verify_url = url_for(
            "verifyemail", token=generated_email_token, _external=True)
        app.logger.debug("verify url= %s", verify_url)
        verify_email_html_page = render_template(
            "verify_email.html", verify_url=verify_url)
        subject = "Please verify your email"
        # send_email(email, subject, verify_email_html_page)-------------------------------------------------------------------==============
        app.logger.debug("Email sent successfully!")

        # when authenticated, return a fresh access token and a refresh token
        # app.logger.debug(f_jwt)

        # access_token = f_jwt.create_access_token(identity=user_id, fresh=True)
        # refresh_token = f_jwt.create_refresh_token(user_id)
        # return {
        #     'access_token': access_token,
        #     'refresh_token': refresh_token
        # }, 201
        return f"verification Email sent to {email} successfully!", 201


class RegisterSeller(Resource):
    def post(self):
        data = request.get_json()
        seller_name = data.get("seller_name", None)
        email = data.get("email", None)
        password = data.get("password", None)
        GSTIN = data.get("GSTIN", None)
        PAN = data.get("PAN", None)

        if not email or not password:
            abort(400, 'Bad Request')
        # check if seller of given email already exists
        CHECK_EMAIL = 'SELECT id FROM sellers WHERE email= %s'
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(CHECK_EMAIL, (email,))
            row = cursor.fetchone()
            if row is not None:
                abort(400, 'Bad Request')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        # user doesn't exists..now create user with hashed password
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt())
        hashed_password = hashed_password.decode('utf-8')

        REGISTER_SELLER = '''INSERT INTO sellers(seller_name, email, hashed_password, "GSTIN", "PAN" , added_at)
        VALUES(%s, %s, %s, %s, %s, %s) RETURNING id'''

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(REGISTER_SELLER, (seller_name, email,
                           hashed_password, GSTIN, PAN, datetime.now(),))
            seller_id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        app.logger.debug(
            "seller with id %s and type = seller created successfully", seller_id)

        # generate token for sending in email for email verification
        generated_email_token = generate_email_token(email)
        app.logger.debug("Generated email token= %s", generated_email_token)

        # send email
        # verify_url = url_for("accounts.verify_email", token=generate_email_token, _external=True)
        verify_url = url_for(
            "verifyemail", token=generated_email_token, _external=True)
        app.logger.debug("verify url= %s", verify_url)
        verify_email_html_page = render_template(
            "verify_email.html", verify_url=verify_url)
        subject = "Please verify your email"
        # send_email(email, subject, verify_email_html_page)-------------------------------------------------------------------==============
        app.logger.debug("Email sent successfully!")

        # when authenticated, return a fresh access token and a refresh token
        # app.logger.debug(f_jwt)

        # access_token = f_jwt.create_access_token(identity=user_id, fresh=True)
        # refresh_token = f_jwt.create_refresh_token(user_id)
        # return {
        #     'access_token': access_token,
        #     'refresh_token': refresh_token
        # }, 201
        return f"verification Email sent to {email} successfully!", 201


class RegisterAdmin(Resource):
    def post(self):
        data = request.get_json()
        first_name = data.get("first_name", None)
        last_name = data.get("last_name", None)
        email = data.get("email", None)
        password = data.get("password", None)
        dob = data.get("dob", None)
        gender = data.get("gender", None)

        if not email or not password:
            abort(400, 'Bad Request')
        # check if user of given email already exists
        CHECK_EMAIL = 'SELECT id FROM admins WHERE email= %s'
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(CHECK_EMAIL, (email,))
            row = cursor.fetchone()
            if row is not None:
                abort(400, 'Bad Request')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        # user doesn't exists..now create user with hashed password
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt())
        hashed_password = hashed_password.decode('utf-8')

        REGISTER_CUSTOMER = '''INSERT INTO admins(first_name, last_name, email, hashed_password, 
        dob, gender, added_at)
        VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id'''

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(REGISTER_CUSTOMER, (first_name, last_name,
                           email, hashed_password, dob, gender, datetime.now(),))
            admin_id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        app.logger.debug(
            "admin with id %s and type = admin created successfully", admin_id)

        # generate token for sending in email for email verification
        generated_email_token = generate_email_token(email)
        app.logger.debug("Generated email token= %s", generated_email_token)

        # send email
        # verify_url = url_for("accounts.verify_email", token=generate_email_token, _external=True)
        verify_url = url_for(
            "verifyemail", token=generated_email_token, _external=True)
        app.logger.debug("verify url= %s", verify_url)
        verify_email_html_page = render_template(
            "verify_email.html", verify_url=verify_url)
        subject = "Please verify your email"
        # send_email(email, subject, verify_email_html_page)-------------------------------------------------------------------==============
        app.logger.debug("Email sent successfully!")

        # when authenticated, return a fresh access token and a refresh token
        # app.logger.debug(f_jwt)

        # access_token = f_jwt.create_access_token(identity=user_id, fresh=True)
        # refresh_token = f_jwt.create_refresh_token(user_id)
        # return {
        #     'access_token': access_token,
        #     'refresh_token': refresh_token
        # }, 201
        return f"verification Email sent to {email} successfully!", 201


class LoginCustomer(Resource):
    def post(self):
        data = request.get_json()
        email = data.get("email", None)
        password = data.get("password", None)

        if not email or not password:
            abort(400, 'Bad Request')

        # check if user of given email already exists
        GET_Customer = 'SELECT id, hashed_password, is_verified FROM customers WHERE email= %s'
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_Customer, (email,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request: User not found')
            else:
                customer_id = row.id
                hashed_password = row.hashed_password
                is_verified = row.is_verified
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        # check user's entered password's hash with db's stored hashed password
        if (bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')) == False):
            abort(400, 'Email or password not correct')

        user_type = "customer"
        if is_verified:
            access_token = f_jwt.create_access_token(
                identity=customer_id, additional_claims={"user_type": user_type}, fresh=True)
            refresh_token = f_jwt.create_refresh_token(
                identity=customer_id, additional_claims={"user_type": user_type})
            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }, 202
        else:
            # generate for sending token in email for email verification
            generated_email_token = generate_email_token(email)
            app.logger.debug("Generated email token= %s",
                             generated_email_token)

            # send email
            # verify_url = url_for("accounts.verify_email", token=generate_email_token, _external=True)
            verify_url = url_for(
                "verifyemail", token=generated_email_token, _external=True)
            app.logger.debug("verify url= %s", verify_url)
            verify_email_html_page = render_template(
                "verify_email.html", verify_url=verify_url)
            subject = "Please verify your email"
            # send_email(email, subject, verify_email_html_page)/-------------------------------------------------------------------------
            app.logger.debug("Email sent successfully!")
            return f"verification Email sent to {email} successfully!", 201


class LoginSeller(Resource):
    def post(self):
        data = request.get_json()
        email = data.get("email", None)
        password = data.get("password", None)

        if not email or not password:
            abort(400, 'Bad Request')

        # check if user of given email already exists
        GET_SELLER = 'SELECT id, hashed_password, is_verified FROM sellers WHERE email= %s'
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_SELLER, (email,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request: User not found')
            else:
                seller_id = row.id
                hashed_password = row.hashed_password
                is_verified = row.is_verified
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        # check user's entered password's hash with db's stored hashed password
        if (bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')) == False):
            abort(400, 'Email or password not correct')

        user_type = "seller"
        if is_verified:
            access_token = f_jwt.create_access_token(
                identity=seller_id, additional_claims={"user_type": user_type}, fresh=True)
            refresh_token = f_jwt.create_refresh_token(
                identity=seller_id, additional_claims={"user_type": user_type})
            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }, 202
        else:
            # generate for sending token in email for email verification
            generated_email_token = generate_email_token(email)
            app.logger.debug("Generated email token= %s",
                             generated_email_token)

            # send email
            # verify_url = url_for("accounts.verify_email", token=generate_email_token, _external=True)
            verify_url = url_for(
                "verifyemail", token=generated_email_token, _external=True)
            app.logger.debug("verify url= %s", verify_url)
            verify_email_html_page = render_template(
                "verify_email.html", verify_url=verify_url)
            subject = "Please verify your email"
            # send_email(email, subject, verify_email_html_page)/-------------------------------------------------------------------------
            app.logger.debug("Email sent successfully!")
            return f"verification Email sent to {email} successfully!", 201


class LoginAdmin(Resource):
    def post(self):
        data = request.get_json()
        email = data.get("email", None)
        password = data.get("password", None)

        if not email or not password:
            abort(400, 'Bad Request')

        # check if user of given email already exists
        GET_Customer = 'SELECT id, hashed_password, is_verified, is_super_admin FROM admins WHERE email= %s'
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_Customer, (email,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request: User not found')
            else:
                admin_id = row.id
                hashed_password = row.hashed_password
                is_verified = row.is_verified
                is_super_admin = row.is_super_admin
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        # check user's entered password's hash with db's stored hashed password
        if (bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')) == False):
            abort(400, 'Email or password not correct')

        if is_super_admin:
            user_type = "super_admin"
        else:
            user_type = "admin"

        if is_verified:
            access_token = f_jwt.create_access_token(
                identity=admin_id, additional_claims={"user_type": user_type}, fresh=True)
            refresh_token = f_jwt.create_refresh_token(
                identity=admin_id, additional_claims={"user_type": user_type})
            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }, 202
        else:
            # generate for sending token in email for email verification
            generated_email_token = generate_email_token(email)
            app.logger.debug("Generated email token= %s",
                             generated_email_token)

            # send email
            # verify_url = url_for("accounts.verify_email", token=generate_email_token, _external=True)
            verify_url = url_for(
                "verifyemail", token=generated_email_token, _external=True)
            app.logger.debug("verify url= %s", verify_url)
            verify_email_html_page = render_template(
                "verify_email.html", verify_url=verify_url)
            subject = "Please verify your email"
            # send_email(email, subject, verify_email_html_page)/-------------------------------------------------------------------------
            app.logger.debug("Email sent successfully!")
            return f"verification Email sent to {email} successfully!", 201


class RefreshToken(Resource):
    @f_jwt.jwt_required(refresh=True)
    def post(self):
        # retrive the user's identity from the refresh token using a Flask-JWT-Extended built-in method
        curent_user_id = f_jwt.get_jwt_identity()
        # app.logger.debug(current_user_id)
        claims = f_jwt.get_jwt()
        current_user_type = claims['user_type']

        # return a non-fresh token for the user
        new_token = f_jwt.create_access_token(
            identity=curent_user_id, additional_claims={"user_type": current_user_type}, fresh=False)
        return {'access_token': new_token}, 200


class VerifyEmail(Resource):
    def get(self):
        args = request.args  # retrieve args from query string
        user_type = args.get('user_type', None)
        token = args.get('token', None)
        app.logger.debug("?user_type=%s", user_type)
        app.logger.debug("?token=%s", token)
        if not (user_type and token):
            abort(400, 'Bad Request')
        if user_type not in ['customer', 'seller', 'admin']:
            abort(400, 'Bad Request')

        try:
            email = verify_email_token(token)
        except:
            flash('The verification link is invalid or has expired.', 'danger')

        # check if user of given email is verified or not
        GET_USER = 'SELECT id, is_verified FROM {} WHERE email= %s'.format(
            user_type+'s')
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_USER, (email,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request: User not found')
            else:
                user_id = row.id
                is_verified = row.is_verified
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        if is_verified:
            flash('Account already verified. Please login.', 'success')
        else:
            UPDATE_USER_VERIFIED = 'UPDATE {} SET is_verified= %s, verified_at= %s WHERE id= %s'.format(
                user_type+'s')
            try:
                cursor = app_globals.get_cursor()
                cursor.execute(UPDATE_USER_VERIFIED,
                               (True, datetime.now(), user_id,))
                if cursor.rowcount != 1:
                    abort(400, 'Bad Request: update row error')
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, 'Bad Request')
            finally:
                cursor.close()

            flash('You have verified your account. Thanks!', 'success')
        # return redirect(url_for('main.home'))
        # todo : pass here homepage url for KalaKriti frontend
        redirect_url = "homepage url for KalaKriti frontend"
        # return redirect(redirect_url)
        return f"redirect url= {redirect_url}", 200

class Register2fa(Resource):
    user_id = f_jwt.get_jwt_identity()
    app.logger.debug("user_id= %s", user_id)
    claims = f_jwt.get_jwt()
    user_type = claims['user_type']
    app.logger.debug("user_type= %s", user_type)

    table_name=user_type+'s'
    


