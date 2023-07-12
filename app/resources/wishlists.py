from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app

from app.resources.product_reviews import get_avg_ratings_and_count
from app.resources.seller import get_seller_info


class Wishlists(Resource):
    @f_jwt.jwt_required()
    def post(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        data = request.get_json()
        product_item_id = data.get("product_item_id", None)

        ADD_TO_WISHLIST = """INSERT INTO wishlists(customer_id,product_item_id, added_at)
                               VALUES(%s, %s, %s)"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                ADD_TO_WISHLIST,
                (
                    customer_id,
                    product_item_id,
                    datetime.now(),
                ),
            )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return (
            f"Product_item_id = {product_item_id} added to wishlist",
            201,
        )

    @f_jwt.jwt_required()
    def get(self):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        wishlists_list = []
        GET_WISHLISTS = """SELECT w.added_at,
        p.id AS product_id, p.product_name, p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
        s.id AS seller_id, s.seller_name, s.email,
        pi.id AS product_item_id, pi.product_variant_name, pi."SKU", 
        pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.product_item_status,
        v.variant, vv.variant_value
        FROM wishlists w
        JOIN product_items pi ON w.product_item_id = pi.id
        JOIN products p ON pi.product_id = p.id
        JOIN sellers s ON p.seller_id = s.id 
        JOIN product_item_values piv ON pi.id = piv.product_item_id
        JOIN variant_values vv ON piv.variant_value_id = vv.id
        JOIN variants v ON vv.variant_id = v.id
        WHERE w.customer_id = %s 
        ORDER BY w.added_at DESC"""

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_WISHLISTS, (customer_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                product_dict = {}
                product_dict.update(
                    json.loads(json.dumps({"added_at": row.added_at}, default=str))
                )
                product_dict["product_id"] = row.product_id
                product_dict["product_name"] = row.product_name
                product_dict["currency"] = row.currency
                product_dict["product_status"] = row.product_status
                product_dict["min_order_quantity"] = row.min_order_quantity
                product_dict["max_order_quantity"] = row.max_order_quantity

                seller_dict = {}
                seller_dict["id"] = row.seller_id
                seller_dict["seller_name"] = row.seller_name
                seller_dict["email"] = row.email
                product_dict.update({"seller": seller_dict})

                product_item_dict = {}
                product_item_dict["id"] = row.product_item_id
                product_item_dict["product_variant_name"] = row.product_variant_name
                product_item_dict["SKU"] = row.SKU

                product_item_dict.update(
                    json.loads(
                        json.dumps({"original_price": row.original_price}, default=str)
                    )
                )
                product_item_dict.update(
                    json.loads(
                        json.dumps({"offer_price": row.offer_price}, default=str)
                    )
                )
                product_item_dict["quantity_in_stock"] = row.quantity_in_stock
                product_item_dict["product_variant_name"] = row.product_variant_name
                product_item_dict["variant"] = row.variant
                product_item_dict["variant_value"] = row.variant_value

                average_rating, rating_count = get_avg_ratings_and_count(
                    cursor, product_dict["product_id"]
                )
                product_dict.update(
                    json.loads(
                        json.dumps({"average_rating": average_rating}, default=str)
                    )
                )
                product_dict["rating_count"] = rating_count

                media_dict = {}
                GET_BASE_MEDIA = """SELECT m.id AS media_id, m.name, m.path
                FROM media m
                WHERE m.id = (SELECT pim.media_id From product_item_medias pim
                WHERE pim.product_item_id = %s 
                ORDER BY pim.display_order LIMIT 1) 
                """
                cursor.execute(GET_BASE_MEDIA, (product_item_dict["id"],))
                row = cursor.fetchone()
                if row is None:
                    app.logger.debug("No media rows")
                    product_item_dict.update({"media": media_dict})
                    product_dict.update({"product_item": product_item_dict})
                    wishlists_list.append(product_dict)
                    continue
                media_dict["id"] = row.media_id
                media_dict["name"] = row.name
                path = row.path
                if path is not None:
                    media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
                else:
                    media_dict["path"] = None
                product_item_dict.update({"media": media_dict})
                product_dict.update({"product_item": product_item_dict})
                wishlists_list.append(product_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(wishlists_list)
        return wishlists_list

    @f_jwt.jwt_required()
    def delete(self, product_item_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        REMOVE_FROM_WISHLIST = (
            "DELETE FROM wishlists WHERE product_item_id= %s AND customer_id =%s"
        )
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                REMOVE_FROM_WISHLIST,
                (
                    product_item_id,
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


class IsItemInWishLists(Resource):
    @f_jwt.jwt_required()
    def get(self, product_item_id):
        customer_id = f_jwt.get_jwt_identity()
        app.logger.debug("customer_id= %s", customer_id)

        IS_ITEM_PRESENT = """SELECT TRUE FROM wishlists WHERE customer_id = %s AND product_item_id = %s"""
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                IS_ITEM_PRESENT,
                (
                    customer_id,
                    product_item_id,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                abort(400, "Bad Request")
            is_item_present = row[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return is_item_present
