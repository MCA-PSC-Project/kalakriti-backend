from datetime import datetime, timezone
import json
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
from flask import current_app as app

from app.resources.product_reviews import get_avg_ratings_and_count


class Search(Resource):
    def get(self):
        args = request.args  # retrieve args from query string
        query = args.get("query", None)
        app.logger.debug("?query=%s", query)
        if not query:
            abort(400, "Bad Request")
        product_status = args.get("product_status", None)
        if not product_status:
            product_status = "published"

        # unquoted text: text not inside quote marks will be converted to terms separated by & operators, as if processed by plainto_tsquery.
        # "quoted text": text inside quote marks will be converted to terms separated by <-> operators, as if processed by phraseto_tsquery.
        # OR : the word “or” will be converted to the | operator.
        # - : a dash will be converted to the ! operator.
        query = query.replace(" ", " or ")

        GET_PRODUCTS = """SELECT p.id AS product_id, p.product_name,
        p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
        p.added_at, p.updated_at, 
        s.id AS seller_id, s.seller_name, s.email,
        pbi.product_item_id AS base_product_item_id
        FROM products p 
        JOIN sellers s ON p.seller_id = s.id 
        JOIN product_base_item pbi ON p.id = pbi.product_id
        WHERE p.id IN (
            SELECT product_id FROM products_tsv_store 
            WHERE tsv @@ websearch_to_tsquery('english', %s)
        ) AND p.product_status = %s"""

        products_list = []
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(
                GET_PRODUCTS,
                (
                    query,
                    product_status,
                ),
            )
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                product_dict = {}
                product_dict["id"] = row.product_id
                product_dict["product_name"] = row.product_name
                product_dict["currency"] = row.currency
                product_dict["product_status"] = row.product_status
                product_dict["min_order_quantity"] = row.min_order_quantity
                product_dict["max_order_quantity"] = row.max_order_quantity
                product_dict.update(
                    json.loads(json.dumps({"added_at": row.added_at}, default=str))
                )
                product_dict.update(
                    json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
                )

                seller_dict = {}
                seller_dict["id"] = row.seller_id
                seller_dict["seller_name"] = row.seller_name
                seller_dict["email"] = row.email
                product_dict.update({"seller": seller_dict})
                product_dict["base_product_item_id"] = row.base_product_item_id

                average_rating, rating_count = get_avg_ratings_and_count(
                    cursor, product_dict["id"]
                )
                product_dict.update(
                    json.loads(
                        json.dumps({"average_rating": average_rating}, default=str)
                    )
                )
                product_dict["rating_count"] = rating_count

                product_item_status = product_status
                GET_PRODUCT_BASE_ITEM = """SELECT pi.id AS product_item_id, pi.product_id, pi.product_variant_name, pi."SKU",
                pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at, pi.product_item_status,
                (SELECT v.variant AS variant FROM variants v WHERE v.id = 
                (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
                (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
                FROM product_items pi 
                JOIN product_item_values piv ON pi.id = piv.product_item_id
                WHERE pi.id= %s AND pi.product_item_status = %s """

                base_product_item_dict = {}
                cursor.execute(
                    GET_PRODUCT_BASE_ITEM,
                    (
                        product_dict["base_product_item_id"],
                        product_item_status,
                    ),
                )
                row = cursor.fetchone()
                if not row:
                    app.logger.debug("No base product item row")
                    product_dict.update({"base_product_item": base_product_item_dict})
                    products_list.append(product_dict)
                    continue
                base_product_item_dict["id"] = row.product_item_id
                base_product_item_dict["product_id"] = row.product_id
                base_product_item_dict[
                    "product_variant_name"
                ] = row.product_variant_name
                base_product_item_dict["SKU"] = row.SKU

                base_product_item_dict.update(
                    json.loads(
                        json.dumps({"original_price": row.original_price}, default=str)
                    )
                )
                base_product_item_dict.update(
                    json.loads(
                        json.dumps({"offer_price": row.offer_price}, default=str)
                    )
                )

                base_product_item_dict["quantity_in_stock"] = row.quantity_in_stock
                base_product_item_dict.update(
                    json.loads(json.dumps({"added_at": row.added_at}, default=str))
                )
                base_product_item_dict.update(
                    json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
                )
                base_product_item_dict["product_item_status"] = row.product_item_status

                base_product_item_dict["variant"] = row.variant
                base_product_item_dict["variant_value"] = row.variant_value

                media_dict = {}
                GET_BASE_MEDIA = """SELECT m.id AS media_id, m.name, m.path
                FROM media m
                WHERE m.id = (
                    SELECT pim.media_id From product_item_medias pim
                    WHERE pim.product_item_id = %s 
                    ORDER BY pim.display_order LIMIT 1
                )"""
                cursor.execute(GET_BASE_MEDIA, (product_dict["base_product_item_id"],))
                row = cursor.fetchone()
                if row is None:
                    app.logger.debug("No media rows")
                    base_product_item_dict.update({"media": media_dict})
                    product_dict.update({"base_product_item": base_product_item_dict})
                    products_list.append(product_dict)
                    continue
                media_dict["id"] = row.media_id
                media_dict["name"] = row.name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    media_dict["path"] = "{}/{}".format(app.config["S3_LOCATION"], path)
                else:
                    media_dict["path"] = None
                base_product_item_dict.update({"media": media_dict})
                product_dict.update({"base_product_item": base_product_item_dict})
                products_list.append(product_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(products_list)
        return products_list


class TopSearches(Resource):
    def get(self):
        queries_list = []
        GET_PRODUCTS = """SELECT query FROM top_searches ORDER BY rank"""
        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_PRODUCTS)
            rows = cursor.fetchall()
            if not rows:
                return []
            for row in rows:
                query = row.query
                queries_list.append(query)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(queries_list)
        return queries_list

    @f_jwt.jwt_required()
    def put(self):
        admin_id = f_jwt.get_jwt_identity()
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        top_searches_list = json.loads(json.dumps(data))

        if user_type != "admin" and user_type != "super_admin":
            abort(403, "Forbidden: only super-admins and admins can post top searches")

        try:
            cursor = app_globals.get_cursor()
            UPSERT_TOP_SEARCHES = """INSERT INTO top_searches(rank, query) VALUES(%s, %s) 
            ON CONFLICT (rank) 
            DO UPDATE SET rank = %s, query = %s"""
            values_tuple_list = []
            for top_search_dict in top_searches_list:
                values_tuple = (
                    top_search_dict.get("rank"),
                    top_search_dict.get("query"),
                    top_search_dict.get("rank"),
                    top_search_dict.get("query"),
                )
                values_tuple_list.append(values_tuple)
            app.logger.debug("values_tuple_list= %s", values_tuple_list)
            psycopg2.extras.execute_batch(
                cursor, UPSERT_TOP_SEARCHES, values_tuple_list
            )
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        return f"top searches updated sucessfully", 201
