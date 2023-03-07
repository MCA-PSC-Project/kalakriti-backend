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

    @f_jwt.jwt_required()
    def get(self,product_id):
        reviews_list = []

        GET_REVIEWS = '''SELECT id,user_id, rating, review , added_at , updated_at FROM product_item_reviews 
                         WHERE product_item_id IN (SELECT id FROM product_items WHERE product_id =%s)'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_REVIEWS,(product_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                review_dict = {}
                review_dict['review_id'] = row.id
                review_dict['user_id'] = row.user_id
                review_dict.update(json.loads(
                    json.dumps({'rating': row.rating}, default=str)))
                review_dict['review'] = row.review
                review_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                review_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))
        
                GET_USER_PROFILE = '''SELECT u.first_name, u.last_name,
                m.id AS media_id, m.name AS media_name, m.path
                FROM users u LEFT JOIN media m on u.dp_id = m.id WHERE u.id = %s'''
                 
                cursor.execute(
                    GET_USER_PROFILE, (review_dict.get('user_id'),))
                row = cursor.fetchone()
                if row is None:
                  return {}
                review_dict['first_name'] = row.first_name
                review_dict['last_name'] = row.last_name
                media_dict={}
                media_dict['id'] = row.media_id
                media_dict['name'] = row.media_name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    media_dict['path'] = None
                
                review_dict.update({"dp": media_dict})
                reviews_list.append(review_dict)

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(banner_dict)
        return reviews_list

    @ f_jwt.jwt_required()
    def put(self, review_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        review_dict = json.loads(json.dumps(data))
        app.logger.debug(review_dict)

        current_time = datetime.now()

        UPDATE_BANNER = 'UPDATE product_item_reviews SET rating= %s, review= %s, updated_at=%s WHERE id= %s and user_id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_BANNER, (review_dict['rating'], review_dict['review'], current_time, review_id, user_id))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"Review_id {review_id} modified."}, 200

    @ f_jwt.jwt_required()
    def delete(self, review_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)

        DELETE_REVIEW = 'DELETE FROM product_item_reviews WHERE id= %s AND user_id =%s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(DELETE_REVIEW, (review_id, user_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200

class GetUserReviewOnProduct(Resource):
    @f_jwt.jwt_required()
    def get(self,product_item_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        reviews_list = []

        GET_REVIEWS = '''SELECT id, rating, review , added_at , updated_at FROM product_item_reviews 
                         WHERE product_item_id = %s AND user_id = %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_named_tuple_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_REVIEWS,(product_item_id,user_id,))
            row = cursor.fetchone()
            if row is None:
                return {}
            # for row in rows:
            review_dict = {}
            review_dict['review_id'] = row.id
            review_dict.update(json.loads(
                json.dumps({'rating': row.rating}, default=str)))
            review_dict['review'] = row.review
            review_dict.update(json.loads(
                json.dumps({'added_at': row.added_at}, default=str)))
            review_dict.update(json.loads(
                json.dumps({'updated_at': row.updated_at}, default=str)))

            GET_USER_PROFILE = '''SELECT u.first_name, u.last_name,
            m.id AS media_id, m.name AS media_name, m.path
            FROM users u LEFT JOIN media m on u.dp_id = m.id WHERE u.id = %s'''
                
            cursor.execute(
                GET_USER_PROFILE, (user_id,))
            row = cursor.fetchone()
            if row is None:
                return {}
            review_dict['first_name'] = row.first_name
            review_dict['last_name'] = row.last_name
            media_dict={}
            media_dict['id'] = row.media_id
            media_dict['name'] = row.media_name
            # media_dict['path'] = row.path
            path = row.path
            if path is not None:
                media_dict['path'] = "{}/{}".format(
                    app.config["S3_LOCATION"], path)
            else:
                media_dict['path'] = None
            
            review_dict.update({"dp": media_dict})
            reviews_list.append(review_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(banner_dict)
        return reviews_list
