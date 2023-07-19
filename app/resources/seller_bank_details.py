from datetime import datetime, timezone
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

        APPLY_FOR_SELLER = """INSERT INTO seller_bank_details(seller_id, account_holder_name, account_no, "IFSC", account_type)
        VALUES(%s, %s, %s, %s, %s) RETURNING id"""
        try:
            cursor = app_globals.get_cursor()

            cursor.execute(
                APPLY_FOR_SELLER,
                (seller_id, account_holder_name, account_no, IFSC, account_type),
            )
            bank_detail_id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return f"seller_id =  {seller_id} bank details entered successfully", 201

    def get(self, seller_id):
        sellers_list = []

        GET_SELLERS_FORM = """SELECT id, account_holder_name, account_no, "IFSC" , account_type FROM seller_bank_details 
        WHERE seller_id= %s"""

        try:
            cursor = app_globals.get_named_tuple_cursor()

            cursor.execute(GET_SELLERS_FORM, (seller_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                sellers_dict = {}
                sellers_dict["id"] = row.id
                sellers_dict["account_holder_name"] = row.account_holder_name
                sellers_dict["account_no"] = row.account_no
                sellers_dict["IFSC"] = row.IFSC
                sellers_dict["account_type"] = row.account_type

                sellers_list.append(sellers_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return sellers_list

    @f_jwt.jwt_required()
    def put(self, bank_detail_id):
        seller_id = f_jwt.get_jwt_identity()
        data = request.get_json()
        seller_bank_detail_dict = json.loads(json.dumps(data))
        # app.logger.debug(seller_form_dict)

        UPDATE_SELLER_FORM = """UPDATE seller_bank_details SET account_holder_name=%s, account_no=%s, "IFSC"=%s,
                       account_type=%s  WHERE id= %s and seller_id= %s"""

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_SELLER_FORM,
                (
                    seller_bank_detail_dict["account_holder_name"],
                    seller_bank_detail_dict["account_no"],
                    seller_bank_detail_dict["IFSC"],
                    seller_bank_detail_dict["account_type"],
                    bank_detail_id,
                    seller_id,
                ),
            )
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"Seller_id {seller_id} bank details modified."}, 200
