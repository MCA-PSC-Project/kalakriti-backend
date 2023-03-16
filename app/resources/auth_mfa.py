from datetime import datetime, timedelta, timezone
import json
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

        mfa_dict = {}
        try:
            cursor = app_globals.get_named_tuple_cursor()

            GET_MFA_STATUS = '''SELECT mfa_enabled FROM {} WHERE id= %s'''.format(
                user_type+'s')
            cursor.execute(GET_MFA_STATUS, (user_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            mfa_dict['mfa_enabled'] = row.mfa_enabled

            GET_MFA_DETAILS = '''SELECT id AS mfa_id, mfa_type, is_default, added_at, updated_at 
            FROM {0} WHERE {1} = %s'''.format(user_type+'s_mfa', user_type+'_id')
            cursor.execute(GET_MFA_DETAILS, (user_id,))
            rows = cursor.fetchall()
            if not rows:
                return mfa_dict
            mfa_items_list = []
            for row in rows:
                mfa_item_dict = {}
                mfa_item_dict['mfa_id'] = row.mfa_id
                mfa_item_dict['mfa_type'] = row.mfa_type
                mfa_item_dict['is_default'] = row.is_default
                mfa_item_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                mfa_item_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))
                mfa_items_list.append(mfa_item_dict)
            mfa_dict.update({"mfa_items": mfa_items_list})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return mfa_dict, 200


class SetupTOTPAuthentication(Resource):
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
            name=user_email, issuer_name=app.config['APP_NAME'])
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

        GET_TOTP_SECRET_KEY = '''SELECT u.mfa_enabled, um.id AS mfa_id, um.secret_key 
        FROM {0} u
        JOIN {1} um ON u.id = um.{2} AND um.mfa_type = 'totp'
        WHERE u.id= %s'''.format(
            user_type+'s', user_type+'s_mfa', user_type+'_id')
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_TOTP_SECRET_KEY, (user_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            mfa_enabled = row.mfa_enabled
            mfa_id = row.mfa_id
            totp_secret_key = row.secret_key
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        if not totp_secret_key:
            abort(400, 'Bad Request')

        totp_matched = otp.verify_totp(totp_secret_key, provided_totp)
        app.logger.debug("totp_matched= %s", totp_matched)
        if not totp_matched:
            abort(400, 'Bad Request: Invalid totp')

        # for enabling mfa using totp
        if user_type == 'super_admin':
            user_type = 'admin'
        # Generate 10 digit backup key
        backup_key = otp.generate_motp(otp_length=10)
        app.logger.debug("backup_key= %s", backup_key)

        hashed_backup_key = bcrypt.hashpw(
            backup_key.encode('utf-8'), bcrypt.gensalt())
        hashed_backup_key = hashed_backup_key.decode('utf-8')

        UPDATE_MFA_ENABLED_HASHED_BACKUP_KEY = '''UPDATE {} SET mfa_enabled= %s, hashed_backup_key= %s,
        updated_at= %s WHERE id= %s'''.format(user_type+'s')
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(UPDATE_MFA_ENABLED_HASHED_BACKUP_KEY,
                           (True, hashed_backup_key, datetime.now(), user_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update {} row error'.format(
                    user_type+'s'))
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()

        MAKE_TOTP_MFA_DEFAULT = '''UPDATE {} SET is_default= %s, updated_at= %s 
        WHERE {} = %s AND mfa_type='totp'
        '''.format(user_type+'s_mfa', user_type+'_id')
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(MAKE_TOTP_MFA_DEFAULT,
                           (True, datetime.now(), user_id))
            if cursor.rowcount != 1:
                app.logger.debug("could not set totp as default mfa")
                # abort(400, 'Bad Request: update {} row error'.format(user_type+'s_mfa'))
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # return "MFA successfully setup with backup key {backup_key}", 201
        return {'mfa_totp_setup': 'success', 'backup_key': backup_key}, 201

        # if mfa is already enabled/login with mfa

        # access_token = f_jwt.create_access_token(
        #     identity=user_id, additional_claims={"user_type": user_type}, fresh=True)
        # refresh_token = f_jwt.create_refresh_token(
        #     identity=user_id, additional_claims={"user_type": user_type})
        # return {
        #     'access_token': access_token,
        #     'refresh_token': refresh_token
        # }, 202

class DisableMFAuthentication(Resource):
    @f_jwt.jwt_required()
    def post(self):
        pass

class TOTPAuthentication(Resource):
    def post(self):
        pass
