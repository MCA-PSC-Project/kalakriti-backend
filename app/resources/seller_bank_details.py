from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Seller_Bank_Details(Resource):
    @f_jwt.jwt_required()
    def post(self):
        seller_id = f_jwt.get_jwt_identity()
        data = request.get_json()
        account_holder_name = data.get("account_holder_name", None)
        account_no = data.get("account_no", None)
        IFSC = data.get("IFSC", None)
        account_type = data.get("account_type", None)

        APPLY_FOR_SELLER = '''INSERT INTO seller_bank_details(seller_id, account_holder_name, account_no, "IFSC", account_type)
        VALUES(%s, %s, %s, %s, %s) RETURNING id'''
        try:
            cursor = app_globals.get_cursor()

            cursor.execute(
                APPLY_FOR_SELLER, (seller_id, account_holder_name, account_no, IFSC, account_type))
            id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return f"seller_id =  {seller_id} bank details entered successfully", 201

    def get(self, seller_id):
        sellers_list = []

        GET_SELLERS_FORM = '''SELECT id, account_holder_name, account_no, "IFSC" , account_type FROM seller_bank_details 
        WHERE seller_id= %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_SELLERS_FORM, (seller_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                sellers_dict = {}
                sellers_dict['id'] = row.id
                sellers_dict['account_holder_name'] = row.account_holder_name
                sellers_dict['account_no'] = row.account_no
                sellers_dict['IFSC'] = row.IFSC
                sellers_dict['account_type'] = row.account_type

                sellers_list.append(sellers_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return sellers_list

    # @ f_jwt.jwt_required()
    # def put(self, seller_id):
    #     data = request.get_json()
    #     seller_form_dict = json.loads(json.dumps(data))
    #     # app.logger.debug(seller_form_dict)

    #     current_time = datetime.now()

    #     UPDATE_SELLER_FORM = '''UPDATE seller_applicant_forms SET name=%s, email=%s, phone=%s,
    #                     description=%s, updated_at=%s  WHERE id= %s'''

    #     # catch exception for invalid SQL statement
    #     try:
    #         # declare a cursor object from the connection
    #         cursor = app_globals.get_cursor()
    #         # # app.logger.debug("cursor object: %s", cursor)

    #         cursor.execute(
    #             UPDATE_SELLER_FORM, (seller_form_dict['name'], seller_form_dict['email'], seller_form_dict['phone'],
    #                             seller_form_dict['description'], current_time, seller_id,))
    #         # app.logger.debug("row_counts= %s", cursor.rowcount)
    #         if cursor.rowcount != 1:
    #             abort(400, 'Bad Request: update row error')
    #     except (Exception, psycopg2.Error) as err:
    #         app.logger.debug(err)
    #         abort(400, 'Bad Request')
    #     finally:
    #         cursor.close()
    #     return {"message": f"Seller_id {seller_id} modified."}, 200

    # @ f_jwt.jwt_required()
    # def delete(self, seller_id):
    #     user_id = f_jwt.get_jwt_identity()
    #     app.logger.debug("user_id= %s", user_id)
    #     claims = f_jwt.get_jwt()
    #     user_type = claims['user_type']

    #     if user_type != "admin" and user_type != "super_admin":
    #         abort(400, "Only super-admins and admins can delete")

    #     DELETE_SELLER_FORM = 'DELETE FROM seller_applicant_forms WHERE id= %s'

    #     # catch exception for invalid SQL statement
    #     try:
    #         # declare a cursor object from the connection
    #         cursor = app_globals.get_cursor()
    #         # # app.logger.debug("cursor object: %s", cursor)

    #         cursor.execute(DELETE_SELLER_FORM, (seller_id,))
    #         # app.logger.debug("row_counts= %s", cursor.rowcount)
    #         if cursor.rowcount != 1:
    #             abort(400, 'Bad Request: delete row error')
    #     except (Exception, psycopg2.Error) as err:
    #         app.logger.debug(err)
    #         abort(400, 'Bad Request')
    #     finally:
    #         cursor.close()
    #     return 200
