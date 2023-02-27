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
        phone = data.get("phone", None)
        description = data.get("description", None)

        current_time = datetime.now()

        APPLY_FOR_SELLER = '''INSERT INTO seller_applicant_forms(name, email, phone, added_at, description)
        VALUES(%s, %s, %s, %s, %s) RETURNING id'''
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                APPLY_FOR_SELLER, (name, email, phone, current_time, description))
            id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return f"seller_id =  {id} applied successfully", 201

    def get(self):
        sellers_list = []

        GET_SELLERS_FORM = '''SELECT id, name, email, phone, reviewed, added_at, updated_at,
                          approval_status, description FROM seller_applicant_forms'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_SELLERS_FORM)
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                sellers_dict = {}
                sellers_dict['id'] = row.id
                sellers_dict['name'] = row.name
                sellers_dict['email'] = row.email
                sellers_dict['phone'] = row.phone
                sellers_dict['reviewed'] = row.reviewed
                sellers_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                sellers_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))
                sellers_dict['approval_status'] = row.approval_status
                sellers_dict['desciption'] = row.description

                sellers_list.append(sellers_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(sellers_list)
        return sellers_list

    @ f_jwt.jwt_required()
    def put(self, seller_id):
        data = request.get_json()
        seller_form_dict = json.loads(json.dumps(data))
        # app.logger.debug(seller_form_dict)

        current_time = datetime.now()

        UPDATE_SELLER_FORM = '''UPDATE seller_applicant_forms SET name=%s, email=%s, phone=%s, 
                        description=%s, updated_at=%s  WHERE id= %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_SELLER_FORM, (seller_form_dict['name'], seller_form_dict['email'], seller_form_dict['phone'],
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
