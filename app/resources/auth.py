from datetime import datetime, timedelta, timezone
from flask import flash, redirect, render_template, request, abort, jsonify, url_for
from flask_restful import Resource
import flask_jwt_extended as f_jwt
import psycopg2
import app.main as main
import bcrypt
from flask import current_app as app
from app.email_token import generate_email_token, verify_email_token
from app.mail import send_email


class Register(Resource):
    def post(self):
        data = request.get_json()
        email = data.get("email", None)
        password = data.get("password", None)
        name = data.get("name", None)
        email = data.get("email", None)
        phone = data.get("phone", None)
        password = data.get("password", None)
        dob = data.get("dob", None)
        gender = data.get("gender", None)
        current_time = datetime.now()
        # app.logger.debug("cur time : %s", current_time)

        if not email or not password:
            abort(400, 'Bad Request')
        # check if user of given email already exists
        CHECK_EMAIL = 'SELECT id FROM users WHERE email= %s'
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

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

        REGISTER_USER = '''INSERT INTO users(name, email, phone, password, dob, gender, added_at)
        VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(REGISTER_USER, (name, email, phone,
                           hashed_password, dob, gender, current_time,))
            user_id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        # generate for sending token in email for email verification
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
        send_email(email, subject, verify_email_html_page)
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


class Login(Resource):
    def post(self):
        data = request.get_json()
        email = data.get("email", None)
        password = data.get("password", None)

        if not email or not password:
            abort(400, 'Bad Request')

        # check if user of given email already exists
        GET_USER = 'SELECT id, password, is_verified FROM users WHERE email= %s'
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_USER, (email,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request: User not found')
            else:
                user_id = row[0]
                hashed_password = row[1]
                is_verified = row[2]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        # check user's entered password's hash with db's stored hashed password
        if (bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')) == False):
            abort(400, 'Email or password not correct')

        if is_verified:
            access_token = f_jwt.create_access_token(
                identity=user_id, fresh=True)
            refresh_token = f_jwt.create_refresh_token(user_id)
            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }, 202
        else:
            # generate for sending token in email for email verification
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
            send_email(email, subject, verify_email_html_page)
            app.logger.debug("Email sent successfully!")
            return f"verification Email sent to {email} successfully!", 201

class RefreshToken(Resource):
    @f_jwt.jwt_required(refresh=True)
    def post(self):
        # retrive the user's identity from the refresh token using a Flask-JWT-Extended built-in method
        current_user_id = f_jwt.get_jwt_identity()

        # return a non-fresh token for the user
        new_token = f_jwt.create_access_token(
            identity=current_user_id, fresh=False)
        return {'access_token': new_token}, 200


class VerifyEmail(Resource):
    def get(self, token):
        app.logger.debug("verify email called")
        try:
            email = verify_email_token(token)
        except:
            flash('The verification link is invalid or has expired.', 'danger')

        # check if user of given email is verified or not
        GET_USER = 'SELECT id, is_verified FROM users WHERE email= %s'
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_USER, (email,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request: User not found')
            else:
                user_id = row[0]
                is_verified = row[1]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        if is_verified:
            flash('Account already verified. Please login.', 'success')
        else:
            is_verified = True
            current_time = datetime.now()
            # app.logger.debug("cur time : %s", current_time)

            UPDATE_CONFIRM_USER = 'UPDATE users SET is_verified= %s, verified_at= %s WHERE id= %s'

            # catch exception for invalid SQL statement
            try:
                # declare a cursor object from the connection
                cursor = main.db_conn.cursor()
                # app.logger.debug("cursor object: %s", cursor)

                cursor.execute(
                    UPDATE_CONFIRM_USER, (is_verified, current_time, user_id,))
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, 'Bad Request')
            finally:
                cursor.close()

            flash('You have verified your account. Thanks!', 'success')
        # return redirect(url_for('main.home'))
        # todo : pass here homepage url for task tracker frontend
        redirect_url = "homepage url for task tracker frontend"
        # return redirect(redirect_url)
        return f"redirect url= {redirect_url}", 200
