from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Seller_Applicant_Form(Resource):
    @f_jwt.jwt_required()
    def post(self):
        # claims = f_jwt.get_jwt()
        # user_type = claims['user_type']
        # app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        name = data.get("name", None)
        email = data.get("email", None)
        mobile_no = data.get("mobile_no", None)
        description = data.get("description", None)

        current_time = datetime.now()

        APPLY_FOR_SELLER = '''INSERT INTO seller_applicant_forms(name, email, mobile_no, added_at, description)
        VALUES(%s, %s, %s, %s, %s) RETURNING id'''
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                APPLY_FOR_SELLER, (name, email, mobile_no, current_time, description))
            id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return f"seller_id =  {id} applied successfully", 201

    def get(self):
        sellers_list = []

        GET_SELLERS_FORM = '''SELECT id, name, email, mobile_no, reviewed, TO_CHAR(added_at, 'YYYY-MM-DD'),
                          approval_status, description FROM seller_applicant_forms'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_SELLERS_FORM)
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                sellers_dict = {}
                sellers_dict['id'] = row[0]
                sellers_dict['name'] = row[1]
                sellers_dict['email'] = row[2]
                sellers_dict['mobile_no'] = row[3]
                sellers_dict['reviewed'] = row[4]
                sellers_dict['added_at'] = row[5]
                sellers_dict['approval_status'] = row[6]
                sellers_dict['desciption'] = row[7]

                sellers_list.append(sellers_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(banner_dict)
        return sellers_list

    @ f_jwt.jwt_required()
    def put(self, seller_id):
        data = request.get_json()
        seller_form_dict = json.loads(json.dumps(data))
        app.logger.debug(seller_form_dict)

        current_time = datetime.now()

        UPDATE_BANNER = '''UPDATE seller_applicant_forms SET name=%s, email=%s, mobile_no=%s, 
                        description=%s, updated_at=%s  WHERE id= %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_BANNER, (seller_form_dict['name'], seller_form_dict['email'], seller_form_dict['mobile_no'],
                                seller_form_dict['description'], current_time, seller_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"Seller_id {seller_id} modified."}, 200

    @ f_jwt.jwt_required()
    def delete(self, seller_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "Only super-admins and admins can delete")

        DELETE_SELLER_FORM = 'DELETE FROM seller_applicant_forms WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(DELETE_SELLER_FORM, (seller_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200
