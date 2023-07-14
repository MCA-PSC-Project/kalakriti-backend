from datetime import datetime, timezone
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app
from app.resources.media import delete_medias_by_ids


def get_avg_ratings_and_count(cursor, product_id):
    GET_AVERAGE_RATING_AND_COUNT = """SELECT COALESCE(AVG(rating),0) AS average_rating, 
    COUNT(rating) AS rating_count FROM product_reviews WHERE product_id = %s"""
    cursor.execute(GET_AVERAGE_RATING_AND_COUNT, (product_id,))
    row = cursor.fetchone()
    average_rating = row.average_rating
    rating_count = row.rating_count
    return average_rating, rating_count


class ProductReview(Resource):
    @f_jwt.jwt_required()
    def post(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        review_media_dict = json.loads(json.dumps(data))
        # review_media_dict = review_dict["review_medias"][0]
        order_item_id = data.get("order_item_id", None)
        app.logger.debug("order_item_id= %s", order_item_id)
        rating = data.get("rating", None)
        review = data.get("review", None)
        current_time = datetime.now(timezone.utc)

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
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

            GET_PRODUCT_ID = """SELECT product_id FROM product_items WHERE id = %s"""
            cursor.execute(GET_PRODUCT_ID, (product_item_id,))
            row = cursor.fetchone()
            if not row:
                app.logger.debug("product_id not found for the given order_item_id!")
                app_globals.db_conn.rollback()
                abort(400, "Bad Request")
            product_id = row[0]

            CREATE_REVIEW = """INSERT INTO product_reviews(customer_id, product_id, rating, review, added_at)
            VALUES(%s, %s, %s, %s, %s) RETURNING id"""
            cursor.execute(
                CREATE_REVIEW,
                (
                    customer_id,
                    product_id,
                    rating,
                    review,
                    current_time,
                ),
            )
            review_id = cursor.fetchone()[0]

            INSERT_REVIEW_MEDIAS = """INSERT INTO product_review_medias(product_review_id, media_id, display_order)
            VALUES(%s, %s, %s)"""

            media_id_list = review_media_dict.get("media_list")
            values_tuple_list = []
            for media_dict in media_id_list:
                values_tuple = (
                    review_id,
                    media_dict.get("media_id"),
                    media_dict.get("display_order"),
                )
                values_tuple_list.append(values_tuple)
            app.logger.debug("values_tuple_list= %s", values_tuple_list)
            psycopg2.extras.execute_batch(
                cursor, INSERT_REVIEW_MEDIAS, values_tuple_list
            )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            app_globals.db_conn.rollback()
            app_globals.db_conn.autocommit = True
            app.logger.debug("autocommit switched back from off to on")
            abort(400, "Bad Request")
        finally:
            cursor.close()
        app_globals.db_conn.commit()
        app_globals.db_conn.autocommit = True
        return (
            f"Review id = {review_id} created sucessfully for product id = {product_id}",
            201,
        )

    def get(self, product_id):
        reviews_list = []
        GET_REVIEWS = """SELECT id, customer_id, rating, review, added_at, updated_at 
        FROM product_reviews 
        WHERE product_id = %s"""

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
                FROM customers c 
                LEFT JOIN media m on c.dp_id = m.id WHERE c.id = %s"""

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
        # app.logger.debug(reviews_list)
        return reviews_list

    @f_jwt.jwt_required()
    def put(self, review_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", customer_id)

        data = request.get_json()
        review_dict = json.loads(json.dumps(data))
        app.logger.debug(review_dict)

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        try:
            cursor = app_globals.get_cursor()
            UPDATE_REVIEW = """UPDATE product_reviews SET rating= %s, review= %s, updated_at= %s 
            WHERE id= %s AND customer_id= %s"""
            cursor.execute(
                UPDATE_REVIEW,
                (
                    review_dict["rating"],
                    review_dict["review"],
                    datetime.now(timezone.utc),
                    review_id,
                    customer_id,
                ),
            )
            if cursor.rowcount != 1:
                abort(400, "Bad Request: update product_review row error")

            if "media_list" in data.keys():
                media_list = data["media_list"]
                GET_MEDIA_IDS = """SELECT media_id FROM product_review_medias WHERE product_review_id = %s"""
                cursor = app_globals.get_named_tuple_cursor()
                cursor.execute(GET_MEDIA_IDS, (review_id,))
                rows = cursor.fetchall()
                old_media_ids_set = set()
                for row in rows:
                    old_media_ids_set.add(row.media_id)
                app.logger.debug("old_media_ids_set= %s", old_media_ids_set)

                values_tuple_list = []
                new_media_ids_set = set()
                for media_dict in media_list:
                    media_id = media_dict.get("media_id")
                    new_media_ids_set.add(media_id)
                    display_order = media_dict.get("display_order")
                    values_tuple = (review_id, media_id, display_order)
                    values_tuple_list.append(values_tuple)
                app.logger.debug("new_media_ids_set= %s", new_media_ids_set)
                media_ids_to_be_deleted_set = old_media_ids_set - new_media_ids_set
                app.logger.debug(
                    "media_ids_to_be_deleted_set= %s", media_ids_to_be_deleted_set
                )
                # if set is not empty
                if media_ids_to_be_deleted_set:
                    result = delete_medias_by_ids(tuple(media_ids_to_be_deleted_set))
                    if not result:
                        app.logger.debug("Error deleting medias from bucket")
                        abort(400, "Bad Request")

                DELETE_ITEM_OLD_MEDIAS = (
                    """DELETE FROM product_review_medias WHERE product_review_id = %s"""
                )
                cursor.execute(DELETE_ITEM_OLD_MEDIAS, (review_id,))
                # do not use row count here

                app.logger.debug("values_tuple_list= %s", values_tuple_list)
                INSERT_REVIEW_MEDIAS = """INSERT INTO product_review_medias(product_review_id, media_id, display_order)
                VALUES(%s, %s, %s)"""
                psycopg2.extras.execute_batch(
                    cursor, INSERT_REVIEW_MEDIAS, values_tuple_list
                )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            app_globals.db_conn.rollback()
            app_globals.db_conn.autocommit = True
            app.logger.debug("autocommit switched back from off to on")
            abort(400, "Bad Request")
        finally:
            cursor.close()
        app_globals.db_conn.commit()
        app_globals.db_conn.autocommit = True
        return {"message": f"Review_id {review_id} modified."}, 200

    @f_jwt.jwt_required()
    def delete(self, review_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", customer_id)

        DELETE_REVIEW = (
            """DELETE FROM product_reviews WHERE id = %s AND customer_id = %s"""
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


class CustomerReviewOnProduct(Resource):
    @f_jwt.jwt_required()
    def get(self, product_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        GET_REVIEW = """SELECT id, rating, review, added_at, updated_at FROM product_reviews 
        WHERE product_id = %s AND customer_id = %s"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(
                GET_REVIEW,
                (
                    product_id,
                    customer_id,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                abort(400, "Bad Request")
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
            FROM customers c 
            LEFT JOIN media m on c.dp_id = m.id WHERE c.id = %s"""

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
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return review_dict
