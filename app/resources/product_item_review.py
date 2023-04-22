from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class ProductItemReview(Resource):
    @f_jwt.jwt_required()
    def post(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)
        # TODO: check seller

        data = request.get_json()
        order_item_id = data.get("order_item_id", None)
        app.logger.debug("order_item_id= %s", order_item_id)

        rating = data.get("rating", None)
        review = data.get("review", None)
        current_time = datetime.now()
        try:
            cursor = app_globals.get_cursor()
            GET_PRODUCT_ITEM_ID = (
                """SELECT product_item_id FROM order_items WHERE id = %s"""
            )
            cursor.execute(GET_PRODUCT_ITEM_ID, (order_item_id,))
            row = cursor.fetchone()
            if not row:
                app.logger.debug(
                    "product_item_id not found for the given order_item_id!"
                )
                app_globals.db_conn.rollback()
                abort(400, "Bad Request")
            product_item_id = row[0]

            CREATE_REVIEW = """INSERT INTO product_item_reviews(customer_id, order_item_id, product_item_id, rating, review, added_at)
            VALUES(%s, %s, %s, %s, %s, %s) RETURNING id"""
            cursor.execute(
                CREATE_REVIEW,
                (
                    customer_id,
                    order_item_id,
                    product_item_id,
                    rating,
                    review,
                    current_time,
                ),
            )
            review_id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return (
            f"Review id = {review_id} created sucessfully for product item id = {product_item_id}",
            201,
        )

    @f_jwt.jwt_required()
    def get(self, product_id):
        reviews_list = []
        GET_REVIEWS = """SELECT id,customer_id, rating, review, added_at, updated_at FROM product_item_reviews 
                         WHERE product_item_id IN (SELECT id FROM product_items WHERE product_id =%s)"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_REVIEWS, (product_id,))
            rows = cursor.fetchall()
            if not rows:
                return []
            for row in rows:
                review_dict = {}
                review_dict["review_id"] = row.id
                review_dict["customer_id"] = row.customer_id
                review_dict.update(
                    json.loads(json.dumps({"rating": row.rating}, default=str))
                )
                review_dict["review"] = row.review
                review_dict.update(
                    json.loads(json.dumps({"added_at": row.added_at}, default=str))
                )
                review_dict.update(
                    json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
                )

                GET_USER_PROFILE = """SELECT c.first_name, c.last_name,
                m.id AS media_id, m.name AS media_name, m.path
                FROM customers c LEFT JOIN media m on c.dp_id = m.id WHERE c.id = %s"""

                cursor.execute(GET_USER_PROFILE, (review_dict.get("customer_id"),))
                row = cursor.fetchone()
                if row is None:
                    return {}
                review_dict["first_name"] = row.first_name
                review_dict["last_name"] = row.last_name
                media_dict = {}
                media_dict["id"] = row.media_id
                media_dict["name"] = row.media_name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
                else:
                    media_dict["path"] = None

                review_dict.update({"dp": media_dict})
                reviews_list.append(review_dict)

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(banner_dict)
        return reviews_list

    @f_jwt.jwt_required()
    def put(self, review_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", customer_id)

        data = request.get_json()
        review_dict = json.loads(json.dumps(data))
        app.logger.debug(review_dict)

        current_time = datetime.now()

        UPDATE_REVIEW = """UPDATE product_item_reviews SET rating= %s, review= %s, updated_at= %s 
        WHERE id= %s AND customer_id= %s"""

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_REVIEW,
                (
                    review_dict["rating"],
                    review_dict["review"],
                    current_time,
                    review_id,
                    customer_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return {"message": f"Review_id {review_id} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self, review_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", customer_id)

        DELETE_REVIEW = (
            """DELETE FROM product_item_reviews WHERE id= %s AND customer_id =%s"""
        )
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                DELETE_REVIEW,
                (
                    review_id,
                    customer_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: delete row error")
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return 200


class GetCustomerReviewOnProduct(Resource):
    @f_jwt.jwt_required()
    def get(self, product_item_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        reviews_list = []

        GET_REVIEWS = """SELECT id, rating, review, added_at, updated_at FROM product_item_reviews 
                         WHERE product_item_id = %s AND customer_id = %s"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(
                GET_REVIEWS,
                (
                    product_item_id,
                    customer_id,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                return {}
            review_dict = {}
            review_dict["review_id"] = row.id
            review_dict.update(
                json.loads(json.dumps({"rating": row.rating}, default=str))
            )
            review_dict["review"] = row.review
            review_dict.update(
                json.loads(json.dumps({"added_at": row.added_at}, default=str))
            )
            review_dict.update(
                json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
            )

            GET_USER_PROFILE = """SELECT c.first_name, c.last_name,
            m.id AS media_id, m.name AS media_name, m.path
            FROM customers c LEFT JOIN media m on c.dp_id = m.id WHERE c.id = %s"""

            cursor.execute(GET_USER_PROFILE, (customer_id,))
            row = cursor.fetchone()
            if row is None:
                return {}
            review_dict["first_name"] = row.first_name
            review_dict["last_name"] = row.last_name
            media_dict = {}
            media_dict["id"] = row.media_id
            media_dict["name"] = row.media_name
            # media_dict['path'] = row.path
            path = row.path
            if path is not None:
                media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
            else:
                media_dict["path"] = None

            review_dict.update({"dp": media_dict})
            reviews_list.append(review_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return reviews_list
