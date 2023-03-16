from datetime import datetime, timedelta, timezone
from flask import flash, redirect, render_template, request, abort, jsonify, url_for
from flask_restful import Resource
import flask_jwt_extended as f_jwt
import psycopg2
import app.app_globals as app_globals
import bcrypt
from flask import current_app as app
import app.otp as otp


class MFAStatus(Resource):
    # get status of MFA
    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        table_name = user_type+'s'
        GET_USER_EMAIL = '''SELECT mfa_enabled FROM {} WHERE id= %s'''.format(
            table_name)
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_USER_EMAIL, (user_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            mfa_enabled = row.mfa_enabled
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"mfa_enabled": mfa_enabled}, 200


class TOTPAuthenticationSetup(Resource):
    # get secret key with provisioning uri
    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if user_type == 'super_admin':
            user_type = 'admin'
        table_name = user_type+'s'
        GET_USER_EMAIL = '''SELECT email FROM {} WHERE id= %s'''.format(
            table_name)
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_USER_EMAIL, (user_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            user_email = row.email
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        totp_secret_key, provisioning_uri = otp.generate_totp_key_with_uri(
            name=user_email, issuer_name='KalaKriti')
        UPSERT_TOTP_SECRET_KEY = '''INSERT INTO {0} ({1}, secret_key, added_at) VALUES(%s, %s, %s)
        ON CONFLICT ({1}, mfa_type)
        DO UPDATE set secret_key= %s, updated_at= %s'''.format(
            table_name+'_mfa', user_type+'_id')
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(UPSERT_TOTP_SECRET_KEY,
                           (user_id, totp_secret_key, datetime.now(), totp_secret_key, datetime.now(),))
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"totp_secret_key": totp_secret_key, "provisioning_uri": provisioning_uri}, 201

    # register MFA(totp)
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        provided_totp = data.get('totp', None)
        if not provided_totp:
            app.logger.debug("No totp provided")
            abort(400, 'Bad Request')

        if user_type == 'super_admin':
            user_type = 'admin'

        GET_TOTP_SECRET_KEY = '''SELECT u.mfa_enabled, um.secret_key 
        FROM {} u
        JOIN {} um u.id = um.{} 
        WHERE id= %s'''.format(
            user_type+'s', user_type+'_mfa', user_type+'_id')
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_TOTP_SECRET_KEY, (user_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            mfa_enabled = row.mfa_enabled
            totp_secret_key = row.totp_secret_key
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        if not totp_secret_key:
            abort(400, 'Bad Request')

        is_verified = otp.verify_totp(totp_secret_key, provided_totp)
        app.logger.debug("is_verified= %s", is_verified)
        if not is_verified:
            abort(400, 'Bad Request: Invalid totp')

        # for enabling mfa using totp
        if not mfa_enabled:
            if user_type == 'super_admin':
                user_type = 'admin'
            # TODO: Generate 10 digit backup key
            backup_key = otp.generate_motp(otp_length=10)
            app.logger.debug(backup_key)

            hashed_backup_key = bcrypt.hashpw(
                backup_key.encode('utf-8'), bcrypt.gensalt())
            hashed_backup_key = hashed_backup_key.decode('utf-8')

            UPDATE_MFA_ENABLED_HASHED_BACKUP_KEY = '''UPDATE {} SET (mfa_enabled, hashed_backup_key, updated_at) 
            VALUES(%s, %s, %s) WHERE id= %s'''.format(user_type+'s')
            try:
                cursor = app_globals.get_cursor()
                cursor.execute(UPDATE_MFA_ENABLED_HASHED_BACKUP_KEY,
                               (True, hashed_backup_key, datetime.now(), user_id))
            except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, 'Bad Request')
            finally:
                cursor.close()
            # return "MFA successfully setup with backup key {backup_key}", 201
            return {'mfa_totp_setup': 'success', 'backup_key': backup_key}, 201

        # # if mfa is already enabled/login with mfa
        # access_token = f_jwt.create_access_token(
        #     identity=user_id, additional_claims={"user_type": user_type}, fresh=True)
        # refresh_token = f_jwt.create_refresh_token(
        #     identity=user_id, additional_claims={"user_type": user_type})
        # return {
        #     'access_token': access_token,
        #     'refresh_token': refresh_token
        # }, 202


class Register_2fa(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        # totp_secret_key = otp.generate_totp_secret_key()
        # app.logger.debug("totp_secret_key= %s", totp_secret_key)
        # generated_totp = otp.generate_totp(totp_secret_key)
        # app.logger.debug("generated_totp= %s", generated_totp)
        # sleep(35)
        # is_verified = otp.verify_totp(totp_secret_key, generated_totp)
        # app.logger.debug("is_verified= %s", is_verified)

        if user_type == 'super_admin':
            user_type = 'admin'
        table_name = user_type+'s'
        GET_USER_EMAIL = '''SELECT email, mfa_enabled, default_mfa_type FROM {} WHERE id= %s'''.format(
            table_name)
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_USER_EMAIL, (user_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            user_email = row.email
            mfa_enabled = row.mfa_enabled
            default_mfa_type = row.default_mfa_type
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        if mfa_enabled:
            abort(400, 'Bad Request: MFA already enabled')
        if default_mfa_type == "totp":
            abort(400, 'Bad Request: 2FA with totp already enabled')

        totp_secret_key, provisioning_uri = otp.generate_totp_key_with_uri(
            name=user_email, issuer_name="KalaKriti")
        app.logger.debug("totp_secret_key= %s", totp_secret_key)
        app.logger.debug("provisioning_uri= %s", provisioning_uri)

        INSERT_TOTP_SECRET_KEY = '''UPDATE {} SET (totp_secret_key, updated_at) VALUES(%s, %s)'''.format(
            table_name)
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(INSERT_TOTP_SECRET_KEY,
                           (totp_secret_key, datetime.now(),))
            id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {totp_secret_key, provisioning_uri}, 201


class TOTPAuthentication(Resource):
    pass
