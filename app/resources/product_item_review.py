from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app

class Product_item_review(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)
         # todo: check seller 

        data = request.get_json()
        order_item_id = data.get("order_item_id", None)
        app.logger.debug("order_item_id= %s", order_item_id)
       
        rating = data.get("rating", None)
        review = data.get("review", None)

        current_time = datetime.now()

         # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)
            GET_PRODUCT_ITEM_ID = '''SELECT product_item_id FROM order_items WHERE order_id = %s'''
            cursor.execute(
                    GET_PRODUCT_ITEM_ID, (order_item_id,))
             
            row = cursor.fetchone()
            if not row:
                app.logger.debug("product_item_id not found!")
                app_globals.db_conn.rollback()
            product_item_id = row[0]

            CREATE_REVIEW = '''INSERT INTO product_item_reviews(user_id, order_item_id, product_item_id, rating, review, added_at)
            VALUES(%s, %s, %s, %s, %s, %s) RETURNING id'''

            cursor.execute(
                    CREATE_REVIEW, (user_id, order_item_id, product_item_id, rating, review, current_time,))
            review_id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
                app.logger.debug(err)
                abort(400, 'Bad Request')
        finally:
                cursor.close()
        return f"Review_id = {review_id} created sucessfully for product_item_id ={product_item_id}", 201

    def get(self,id):
        reviews_list = []

        GET_REVIEWS = '''SELECT rating, review , added_at , updated_at FROM product_item_reviews 
                         WHERE product_item_id IN (SELECT id FROM product_items WHERE product_id =%s)'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_REVIEWS,(id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                review_dict = {}
                review_dict.update(json.loads(
                    json.dumps({'rating': row.rating}, default=str)))
                review_dict['review'] = row.review
                review_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                review_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))


                # banner_media_dict = {}
                # banner_media_dict['id'] = row.media_id
                # banner_media_dict['name'] = row.name
                # path = row.path
                # if path is not None:
                #     banner_media_dict['path'] = "{}/{}".format(
                #         app.config["S3_LOCATION"], path)
                # else:
                #     banner_media_dict['path'] = None
                # review_dict.update({"dp": banner_media_dict})

                reviews_list.append(review_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(banner_dict)
        return reviews_list

    # @ f_jwt.jwt_required()
    # def put(self, banner_id):
    #     claims = f_jwt.get_jwt()
    #     user_type = claims['user_type']
    #     app.logger.debug("user_type= %s", user_type)

    #     data = request.get_json()
    #     banner_dict = json.loads(json.dumps(data))
    #     app.logger.debug(banner_dict)

    #     if user_type != "admin" and user_type != "super_admin":
    #         abort(400, "only super-admins and admins can update banners")

    #     UPDATE_BANNER = 'UPDATE banners SET redirect_type= %s, redirect_url= %s WHERE id= %s'

    #     # catch exception for invalid SQL statement
    #     try:
    #         # declare a cursor object from the connection
    #         cursor = app_globals.get_cursor()
    #         # # app.logger.debug("cursor object: %s", cursor)

    #         cursor.execute(
    #             UPDATE_BANNER, (banner_dict['redirect_type'], banner_dict['redirect_url'], banner_id,))
    #         # app.logger.debug("row_counts= %s", cursor.rowcount)
    #         if cursor.rowcount != 1:
    #             abort(400, 'Bad Request: update row error')
    #     except (Exception, psycopg2.Error) as err:
    #         app.logger.debug(err)
    #         abort(400, 'Bad Request')
    #     finally:
    #         cursor.close()
    #     return {"message": f"Banner_id {banner_id} modified."}, 200

    # @ f_jwt.jwt_required()
    # def delete(self, banner_id):
    #     user_id = f_jwt.get_jwt_identity()
    #     app.logger.debug("user_id= %s", user_id)
    #     claims = f_jwt.get_jwt()
    #     user_type = claims['user_type']

    #     if user_type != "admin" and user_type != "super_admin":
    #         abort(400, "Only super-admins and admins can delete banner")

    #     DELETE_BANNER = 'DELETE FROM banners WHERE id= %s'

    #     # catch exception for invalid SQL statement
    #     try:
    #         # declare a cursor object from the connection
    #         cursor = app_globals.get_cursor()
    #         # app.logger.debug("cursor object: %s", cursor)

    #         cursor.execute(DELETE_BANNER, (banner_id,))
    #         # app.logger.debug("row_counts= %s", cursor.rowcount)
    #         if cursor.rowcount != 1:
    #             abort(400, 'Bad Request: delete row error')
    #     except (Exception, psycopg2.Error) as err:
    #         app.logger.debug(err)
    #         abort(400, 'Bad Request')
    #     finally:
    #         cursor.close()
    #     return 200
