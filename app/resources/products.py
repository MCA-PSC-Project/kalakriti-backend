from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app
from app.resources.media import delete_medias_by_ids
from app.resources.product_reviews import get_avg_ratings_and_count


class ProductsByCategory(Resource):
    def get(self):
        args = request.args  # retrieve args from query string
        category_id = args.get("category_id", None)
        subcategory_id = args.get("subcategory_id", None)
        product_status = args.get("product_status", None)
        if not product_status:
            product_status = "published"
        if not category_id and not subcategory_id:
            abort(400, "Bad Request: Provide either category_id or subcategory_id")
        elif not category_id:
            app.logger.debug("?subcategory_id=%s", subcategory_id)
            category_id = subcategory_id
            column_name = "p.subcategory_id"
        elif not subcategory_id:
            app.logger.debug("?category_id=%s", category_id)
            column_name = "p.category_id"
        else:
            abort(400, "Bad Request")

        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_PRODUCTS_BY_CATEGORY = """SELECT p.id AS product_id, p.product_name, 
            p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
            p.added_at, p.updated_at, 
            s.id AS seller_id, s.seller_name, s.email,
            pbi.product_item_id AS base_product_item_id
            FROM products p 
            JOIN sellers s ON p.seller_id = s.id 
            JOIN product_base_item pbi ON p.id = pbi.product_id
            WHERE {} IN (SELECT id FROM categories ct WHERE ct.id = %s) AND p.product_status = %s 
            ORDER BY p.id DESC""".format(
                column_name
            )

            cursor.execute(
                GET_PRODUCTS_BY_CATEGORY,
                (
                    category_id,
                    product_status,
                ),
            )
            rows = cursor.fetchall()
            if not rows:
                return []
            products_list = []
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


class Products(Resource):
    def get(self, product_id):
        args = request.args  # retrieve args from query string
        product_status = args.get("product_status", None)
        if not product_status:
            product_status = "published"
        product_dict = {}
        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_PRODUCT = """SELECT p.id AS product_id, p.product_name, p.product_description, 
            ct.id AS category_id, ct.name AS category_name,
            sct.id AS subcategory_id, sct.name AS subcategory_name, sct.parent_id, 
            p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
            p.added_at, p.updated_at, 
            s.id AS seller_id, s.seller_name, s.email,
            pbi.product_item_id AS base_product_item_id
            FROM products p 
            JOIN categories ct ON p.category_id = ct.id
            LEFT JOIN categories sct ON p.subcategory_id = sct.id
            JOIN sellers s ON p.seller_id = s.id 
            JOIN product_base_item pbi ON p.id = pbi.product_id
            WHERE p.id = %s AND p.product_status = %s"""

            cursor.execute(
                GET_PRODUCT,
                (
                    product_id,
                    product_status,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                abort(400, "Bad Request")
            product_dict["id"] = row.product_id
            product_dict["product_name"] = row.product_name
            product_dict["product_description"] = row.product_description

            category_dict = {}
            category_dict["id"] = row.category_id
            category_dict["name"] = row.category_name
            product_dict.update({"category": category_dict})

            subcategory_dict = {}
            subcategory_dict["id"] = row.subcategory_id
            subcategory_dict["name"] = row.subcategory_name
            subcategory_dict["parent_id"] = row.parent_id
            product_dict.update({"subcategory": subcategory_dict})

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
                json.loads(json.dumps({"average_rating": average_rating}, default=str))
            )
            product_dict["rating_count"] = rating_count

            product_item_status = product_status
            product_items_list = []
            GET_PRODUCT_ITEMS = """SELECT pi.id AS product_item_id, pi.product_id, pi.product_variant_name, pi."SKU", 
            pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at, product_item_status,
            (SELECT v.variant AS variant FROM variants v WHERE v.id = 
            (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
            (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
            FROM product_items pi 
            JOIN product_item_values piv ON pi.id = piv.product_item_id
            WHERE pi.product_id = %s AND pi.product_item_status = %s
            ORDER BY pi.id"""

            cursor.execute(
                GET_PRODUCT_ITEMS,
                (
                    product_id,
                    product_item_status,
                ),
            )
            rows = cursor.fetchall()
            if not rows:
                app.logger.debug("No rows")
                return product_dict
            for row in rows:
                product_item_dict = {}
                product_item_dict["id"] = row.product_item_id
                product_item_dict["product_id"] = row.product_id
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
                product_item_dict.update(
                    json.loads(json.dumps({"added_at": row.added_at}, default=str))
                )
                product_item_dict.update(
                    json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
                )
                product_item_dict["product_item_status"] = row.product_item_status

                product_item_dict["variant"] = row.variant
                product_item_dict["variant_value"] = row.variant_value

                if product_item_dict["id"] == product_dict["base_product_item_id"]:
                    GET_MEDIAS = """SELECT m.id AS media_id, m.name, m.path, pim.display_order
                    FROM product_item_medias pim 
                    JOIN LATERAL
                    (SELECT m.id, m.name, m.path 
                    FROM media m 
                    WHERE m.id = pim.media_id
                    ) AS m ON TRUE
                    WHERE pim.product_item_id= %s
                    ORDER BY pim.display_order"""

                    media_list = []
                    cursor.execute(GET_MEDIAS, (product_dict["base_product_item_id"],))
                    rows = cursor.fetchall()
                    if not rows:
                        # app.logger.debug("No media rows")
                        pass
                    for row in rows:
                        media_dict = {}
                        media_dict["id"] = row.media_id
                        media_dict["name"] = row.name
                        # media_dict['path'] = row[2]
                        path = row.path
                        if path is not None:
                            media_dict["path"] = "{}/{}".format(
                                app.config["S3_LOCATION"], path
                            )
                        else:
                            media_dict["path"] = None
                        media_dict["display_order"] = row.display_order
                        media_list.append(media_dict)
                    product_item_dict.update({"media_list": media_list})

                product_items_list.append(product_item_dict)
            product_dict.update({"product_items": product_items_list})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(product_dict)
        return product_dict


class SellersProducts(Resource):
    @f_jwt.jwt_required()
    def post(self):
        seller_id = f_jwt.get_jwt_identity()
        app.logger.debug("seller_id= %s", seller_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        product_dict = json.loads(json.dumps(data))
        product_item_dict = product_dict["product_items"][0]
        current_time = datetime.now()

        if user_type != "seller":
            abort(400, "only sellers can create products")

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        # print(app_globals.db_conn)
        try:
            cursor = app_globals.get_cursor()
            category_id = product_dict.get("category_id")
            subcategory_id = product_dict.get("subcategory_id")
            if subcategory_id != None:
                CHECK_SUBCATEGORY = """SELECT parent_id FROM categories WHERE id = %s"""
                cursor.execute(CHECK_SUBCATEGORY, (subcategory_id,))
                stored_category_id = cursor.fetchone()[0]
                if category_id != stored_category_id:
                    app.logger.debug("category_id != stored_category_id")
                    abort(400, "Bad request")
            CREATE_PRODUCT = """INSERT INTO products(product_name, product_description, category_id, subcategory_id, 
            currency, seller_id, min_order_quantity, max_order_quantity, added_at) 
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""
            cursor.execute(
                CREATE_PRODUCT,
                (
                    product_dict.get("product_name"),
                    product_dict.get("product_description"),
                    category_id,
                    subcategory_id,
                    product_dict.get("currency", "INR"),
                    seller_id,
                    product_dict.get("min_order_quantity"),
                    product_dict.get("max_order_quantity"),
                    current_time,
                ),
            )
            product_id = cursor.fetchone()[0]

            GET_VARIANT_ID = """SELECT id FROM variants WHERE variant= %s"""
            cursor.execute(GET_VARIANT_ID, (product_item_dict.get("variant").upper(),))
            row = cursor.fetchone()
            if not row:
                app.logger.debug("variant_id not found!")
                app_globals.db_conn.rollback()
            variant_id = row[0]

            CREATE_VARIANT_VALUE = """INSERT INTO variant_values(variant_id, variant_value) VALUES(%s, %s) RETURNING id"""
            cursor.execute(
                CREATE_VARIANT_VALUE,
                (
                    variant_id,
                    product_item_dict.get("variant_value"),
                ),
            )
            variant_value_id = cursor.fetchone()[0]

            CREATE_PRODUCT_ITEM = """INSERT INTO product_items(product_id, product_variant_name, "SKU",
            original_price, offer_price, quantity_in_stock, added_at)
            VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id"""
            cursor.execute(
                CREATE_PRODUCT_ITEM,
                (
                    product_id,
                    product_item_dict.get("product_variant_name"),
                    product_item_dict.get("SKU"),
                    product_item_dict.get("original_price"),
                    product_item_dict.get("offer_price"),
                    product_item_dict.get("quantity_in_stock"),
                    current_time,
                ),
            )
            product_item_id = cursor.fetchone()[0]

            ASSOCIATE_PRODUCT_ITEM_WITH_VARIANT = """INSERT INTO product_item_values(product_item_id, variant_value_id)
            VALUES(%s, %s)"""
            cursor.execute(
                ASSOCIATE_PRODUCT_ITEM_WITH_VARIANT,
                (
                    product_item_id,
                    variant_value_id,
                ),
            )
            # product_item_value_id = cursor.fetchone()[0]

            ASSOCIATE_PRODUCT_WITH_BASE_ITEM = """INSERT INTO product_base_item(product_id, product_item_id)
            VALUES(%s, %s)"""
            cursor.execute(
                ASSOCIATE_PRODUCT_WITH_BASE_ITEM,
                (
                    product_id,
                    product_item_id,
                ),
            )
            # product_base_item_id = cursor.fetchone()[0]

            INSERT_MEDIAS = """INSERT INTO product_item_medias(product_item_id, media_id, display_order)
            VALUES(%s, %s, %s)"""

            media_list = product_item_dict.get("media_list")
            values_tuple_list = []
            for media_dict in media_list:
                values_tuple = (
                    product_item_id,
                    media_dict.get("media_id"),
                    media_dict.get("display_order"),
                )
                values_tuple_list.append(values_tuple)
            app.logger.debug("values_tuple_list= %s", values_tuple_list)
            psycopg2.extras.execute_batch(cursor, INSERT_MEDIAS, values_tuple_list)
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
            f"product_id = {product_id} with product_item_id= {product_item_id} created successfully",
            201,
        )

    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("seller_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)
        args = request.args  # retrieve args from query string
        product_status = args.get("product_status", None)
        if not product_status:
            product_status = "published"

        if user_type == "seller":
            seller_user_id = user_id
        elif user_type == "admin" or user_type == "super_admin":
            seller_user_id = args.get("seller_user_id", None)
            app.logger.debug("?seller_user_id=%s", seller_user_id)
        else:
            abort(
                400, "only sellers, admins and super_admins can view seller's products"
            )

        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_PRODUCTS_BY_SELLER = """SELECT p.id AS product_id, p.product_name, p.product_description, 
            p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
            p.added_at, p.updated_at, 
            s.id AS seller_id, s.seller_name, s.email,
            pbi.product_item_id AS base_product_item_id
            FROM products p 
            JOIN sellers s ON p.seller_id = s.id 
            JOIN product_base_item pbi ON p.id = pbi.product_id
            WHERE p.seller_id = %s AND p.product_status = %s
            ORDER BY p.id DESC"""

            cursor.execute(
                GET_PRODUCTS_BY_SELLER,
                (
                    seller_user_id,
                    product_status,
                ),
            )
            rows = cursor.fetchall()
            if not rows:
                return {}
            products_list = []
            for row in rows:
                product_dict = {}
                product_dict["id"] = row.product_id
                product_dict["product_name"] = row.product_name
                product_dict["product_description"] = row.product_description
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
                WHERE pi.id = %s AND product_item_status = %s"""

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
                WHERE m.id = (SELECT pim.media_id From product_item_medias pim
                WHERE pim.product_item_id = %s 
                ORDER BY pim.display_order LIMIT 1) 
                """
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

    # update product only
    @f_jwt.jwt_required()
    def put(self, product_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        if (
            user_type != "seller"
            and user_type != "admin"
            and user_type != "super_admin"
        ):
            abort(400, "only seller, super-admins and admins can update product")

        app.logger.debug("product_id= %s", product_id)
        data = request.get_json()
        product_dict = json.loads(json.dumps(data))
        # app.logger.debug(product_dict)
        current_time = datetime.now()

        try:
            cursor = app_globals.get_cursor()
            category_id = product_dict.get("caftegory_id")
            subcategory_id = product_dict.get("subcategory_id")
            if subcategory_id != None:
                CHECK_SUBCATEGORY = """SELECT parent_id FROM categories WHERE id = %s"""
                cursor.execute(CHECK_SUBCATEGORY, (subcategory_id,))
                stored_category_id = cursor.fetchone()[0]
                if category_id != stored_category_id:
                    app.logger.debug("category_id != stored_category_id")
                    abort(400, "Bad request")
            UPDATE_PRODUCT = """UPDATE products SET product_name= %s, product_description= %s,
            category_id= %s, subcategory_id= %s, currency= %s, min_order_quantity= %s, max_order_quantity= %s,
            updated_at= %s 
            WHERE id= %s"""
            cursor.execute(
                UPDATE_PRODUCT,
                (
                    product_dict.get("product_name"),
                    product_dict.get("product_description"),
                    product_dict.get("category_id"),
                    product_dict.get("subcategory_id"),
                    product_dict.get("currency", "INR"),
                    product_dict.get("min_order_quantity"),
                    product_dict.get("max_order_quantity"),
                    current_time,
                    product_id,
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
        return {"message": f"product_id {product_id} modified."}, 200

    # update product_status or mark/unmark product as trashed (partially delete)
    @f_jwt.jwt_required()
    def patch(self, product_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("product_id= %s", product_id)
        data = request.get_json()
        current_time = datetime.now()

        if "product_status" in data.keys():
            if user_type != "admin" and user_type != "super_admin" and user_type !="seller":
                abort(
                    400,
                    "only super-admins and admins are allowed to update product status",
                )
          
            
            product_item_status = product_status = data["product_status"]
            # app.logger.debug("product_status= %s", value)

            # before beginning transaction autocommit must be off
            app_globals.db_conn.autocommit = False
            try:
                cursor = app_globals.get_cursor()
                UPDATE_PRODUCT_STATUS = """UPDATE products SET product_status= %s, updated_at= %s
                WHERE id= %s"""
                cursor.execute(
                    UPDATE_PRODUCT_STATUS,
                    (
                        product_status,
                        current_time,
                        product_id,
                    ),
                )
                if cursor.rowcount != 1:
                    abort(400, "Bad Request: update row error")

                # for making base product item status same as product status
                UPDATE_BASE_PRODUCT_ITEM_STATUS = """UPDATE product_items SET product_item_status= %s, updated_at= %s
                WHERE id= (SELECT product_item_id FROM product_base_item WHERE product_id= %s)"""
                cursor.execute(
                    UPDATE_BASE_PRODUCT_ITEM_STATUS,
                    (
                        product_item_status,
                        current_time,
                        product_id,
                    ),
                )
                if cursor.rowcount != 1:
                    abort(400, "Bad Request: update row error")
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

        elif "trashed" in data.keys():
            if (
                user_type != "seller"
                and user_type != "admin"
                and user_type != "super_admin"
            ):
                abort(400, "only seller, super-admins and admins can trash a product")
            value = "trashed" if data["trashed"] else "unpublished"
            # app.logger.debug("trashed= %s", value)
            # before beginning transaction autocommit must be off
            app_globals.db_conn.autocommit = False
            try:
                cursor = app_globals.get_cursor()
                UPDATE_PRODUCT_TRASHED_VALUE = """UPDATE products SET product_status= %s, updated_at= %s
                WHERE id= %s"""
                cursor.execute(
                    UPDATE_PRODUCT_TRASHED_VALUE,
                    (
                        value,
                        current_time,
                        product_id,
                    ),
                )
                if cursor.rowcount != 1:
                    abort(400, "Bad Request: update row error")

                # for making product items status same as product status
                UPDATE_PRODUCT_ITEMS_TRASHED_VALUE = """UPDATE product_items SET product_item_status= %s, updated_at= %s
                WHERE product_id= %s"""
                cursor.execute(
                    UPDATE_PRODUCT_ITEMS_TRASHED_VALUE,
                    (
                        value,
                        current_time,
                        product_id,
                    ),
                )
                if cursor.rowcount == 0:
                    abort(400, "Bad Request: update row error")
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
        else:
            abort(400, "Bad Request")
        return {"message": f"product_id {product_id} modified."}, 200

    # delete trashed product
    @f_jwt.jwt_required()
    def delete(self, product_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)
        app.logger.debug("product_id=%s", product_id)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can delete product")

        app_globals.db_conn.autocommit = False
        try:
            cursor = app_globals.get_named_tuple_cursor()
            # For deleting medias
            media_ids = []
            GET_MEDIA_IDS = """SELECT media_id FROM product_item_medias WHERE product_item_id IN (
                    SELECT pi.id FROM product_items pi WHERE pi.product_id = %s
            )"""
            cursor.execute(GET_MEDIA_IDS, (product_id,))
            rows = cursor.fetchall()
            if not rows:
                abort(400, "Bad Request")
            for row in rows:
                media_ids.append(row.media_id)
            result = delete_medias_by_ids(tuple(media_ids))
            if not result:
                app.logger.debug("Error deleting medias from bucket")
                abort(400, "Bad Request")

            # For deleting variants of product
            DELETE_VARIANT_VALUE = """DELETE FROM variant_values vv WHERE vv.id IN (
                SELECT piv.variant_value_id FROM product_item_values piv 
                WHERE piv.product_item_id IN (
                    SELECT pi.id FROM product_items pi WHERE pi.product_id = %s
                )
            )"""
            cursor.execute(DELETE_VARIANT_VALUE, (product_id,))
            if not cursor.rowcount > 0:
                abort(400, "Bad Request: delete variant values row error")

            # For deleting trashed product
            DELETE_TRASHED_PRODUCT = (
                """DELETE FROM products WHERE id= %s AND product_status='trashed' """
            )
            cursor.execute(DELETE_TRASHED_PRODUCT, (product_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, "Bad Request: delete row error")
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
        app.logger.debug("autocommit switched back from off to on")
        return 200


class ProductsAllDetails(Resource):
    @f_jwt.jwt_required()
    def get(self, product_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims["user_type"]
        app.logger.debug("user_type= %s", user_type)
        app.logger.debug("product_id=%s", product_id)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can see all details of a product")

        product_dict = {}
        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_PRODUCT = """SELECT p.id AS product_id, p.product_name, p.product_description, 
            ct.id AS category_id, ct.name AS category_name,
            sct.id AS subcategory_id, sct.name AS subcategory_name, sct.parent_id, 
            p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
            p.added_at, p.updated_at, 
            s.id AS seller_id, s.seller_name, s.email,
            pbi.product_item_id AS base_product_item_id
            FROM products p 
            JOIN categories ct ON p.category_id = ct.id
            LEFT JOIN categories sct ON p.subcategory_id = sct.id
            JOIN sellers s ON p.seller_id = s.id 
            JOIN product_base_item pbi ON p.id = pbi.product_id
            WHERE p.id= %s"""

            cursor.execute(GET_PRODUCT, (product_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, "Bad Request")
            product_dict["id"] = row.product_id
            product_dict["product_name"] = row.product_name
            product_dict["product_description"] = row.product_description

            category_dict = {}
            category_dict["id"] = row.category_id
            category_dict["name"] = row.category_name
            product_dict.update({"category": category_dict})

            subcategory_dict = {}
            subcategory_dict["id"] = row.subcategory_id
            subcategory_dict["name"] = row.subcategory_name
            subcategory_dict["parent_id"] = row.parent_id
            product_dict.update({"subcategory": subcategory_dict})

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
                json.loads(json.dumps({"average_rating": average_rating}, default=str))
            )
            product_dict["rating_count"] = rating_count

            product_items_list = []
            GET_PRODUCT_ITEMS = """SELECT pi.id AS product_item_id, pi.product_id, pi.product_variant_name, pi."SKU", 
            pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at, pi.product_item_status,
            (SELECT v.variant AS variant FROM variants v WHERE v.id = 
            (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
            (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
            FROM product_items pi 
            JOIN product_item_values piv ON pi.id = piv.product_item_id
            WHERE pi.product_id = %s
            ORDER BY pi.id"""

            cursor.execute(GET_PRODUCT_ITEMS, (product_id,))
            rows = cursor.fetchall()
            if not rows:
                app.logger.debug("No rows")
                return product_dict
            for row in rows:
                product_item_dict = {}
                product_item_dict["id"] = row.product_item_id
                product_item_dict["product_id"] = row.product_id
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
                product_item_dict.update(
                    json.loads(json.dumps({"added_at": row.added_at}, default=str))
                )
                product_item_dict.update(
                    json.loads(json.dumps({"updated_at": row.updated_at}, default=str))
                )
                product_item_dict["product_item_status"] = row.product_item_status

                product_item_dict["variant"] = row.variant
                product_item_dict["variant_value"] = row.variant_value

                GET_MEDIAS = """SELECT m.id AS media_id, m.name, m.path, pim.display_order, pim.media_id AS pim_media_id
                FROM product_item_medias pim 
                JOIN LATERAL
                (SELECT m.id, m.name, m.path 
                FROM media m 
                WHERE m.id = pim.media_id
                ) AS m ON TRUE
                WHERE pim.product_item_id= %s
                ORDER BY pim.display_order"""

                media_list = []
                cursor.execute(GET_MEDIAS, (product_item_dict["id"],))
                rows = cursor.fetchall()
                if not rows:
                    # app.logger.debug("No media rows")
                    pass
                for row in rows:
                    media_dict = {}
                    media_dict["id"] = row.media_id
                    media_dict["name"] = row.name
                    # media_dict['path'] = row[2]
                    path = row.path
                    if path is not None:
                        media_dict["path"] = "{}/{}".format(
                            app.config["S3_LOCATION"], path
                        )
                    else:
                        media_dict["path"] = None
                    media_dict["display_order"] = row.display_order
                    media_dict["pim_media_id"] = row.pim_media_id
                    media_list.append(media_dict)
                product_item_dict.update({"media_list": media_list})

                product_items_list.append(product_item_dict)
            product_dict.update({"product_items": product_items_list})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(product_dict)
        return product_dict


class ProductsByQuery(Resource):
    def get(self):
        args = request.args  # retrieve args from query string
        product_status = args.get("product_status", None)
        product_item_status = args.get("product_item_status", None)
        SKU = args.get("SKU", None)
        min_offer_price = args.get("min_offer_price", None)
        max_offer_price = args.get("max_offer_price", None)
        in_stock = args.get("in_stock", None)
        product_item_where_condition = ""
        if not product_status:
            product_item_status = product_status = "published"
        if SKU:
            product_item_where_condition += ' AND "SKU" = %s'
            product_item_values_tuple = (
                product_item_status,
                SKU,
            )
        else:
            if min_offer_price and max_offer_price:
                product_item_where_condition += (
                    " AND offer_price >= %s AND offer_price <= %s"
                )
                product_item_values_tuple = (
                    product_item_status,
                    min_offer_price,
                    max_offer_price,
                )
            elif min_offer_price and (not max_offer_price):
                product_item_where_condition += " AND offer_price >= %s"
                product_item_values_tuple = (
                    product_item_status,
                    min_offer_price,
                )
            elif (not min_offer_price) and max_offer_price:
                product_item_where_condition += " AND offer_price <= %s"
                product_item_values_tuple = (
                    product_item_status,
                    max_offer_price,
                )
            else:
                abort(400, "Bad request")

        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_PRODUCTS_BY_QUERY = """SELECT p.id AS product_id, p.product_name, 
            p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
            p.added_at AS product_added_at, p.updated_at AS product_updated_at, 
            s.id AS seller_id, s.seller_name, s.email,
            pbi.product_item_id AS base_product_item_id,
            pi.id AS product_item_id, pi.product_id AS pi_product_id, pi.product_variant_name, pi."SKU",
            pi.original_price, pi.offer_price, pi.quantity_in_stock, 
            pi.added_at AS pi_added_at, pi.updated_at AS pi_updated_at, pi.product_item_status,
            (SELECT v.variant AS variant FROM variants v WHERE v.id = 
            (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
            (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
            FROM product_items pi 
            JOIN product_item_values piv ON pi.id = piv.product_item_id
            JOIN products p ON p.id = pi.product_id 
            JOIN sellers s ON s.id = (SELECT p.seller_id FROM products p WHERE p.id = pi.product_id) 
            LEFT JOIN product_base_item pbi ON pbi.product_id = (SELECT p.id FROM products p WHERE p.id = pi.product_id)
            WHERE p.product_status = %s AND pi.product_item_status = %s {}""".format(
                product_item_where_condition
            )

            cursor.execute(
                GET_PRODUCTS_BY_QUERY, (product_status, *product_item_values_tuple)
            )
            rows = cursor.fetchall()
            if not rows:
                return {}
            products_list = []
            for row in rows:
                product_dict = {}
                product_dict["id"] = row.product_id
                product_dict["product_name"] = row.product_name
                product_dict["currency"] = row.currency
                product_dict["product_status"] = row.product_status
                product_dict["min_order_quantity"] = row.min_order_quantity
                product_dict["max_order_quantity"] = row.max_order_quantity
                product_dict.update(
                    json.loads(
                        json.dumps({"added_at": row.product_added_at}, default=str)
                    )
                )
                product_dict.update(
                    json.loads(
                        json.dumps({"updated_at": row.product_updated_at}, default=str)
                    )
                )

                seller_dict = {}
                seller_dict["id"] = row.seller_id
                seller_dict["seller_name"] = row.seller_name
                seller_dict["email"] = row.email
                product_dict.update({"seller": seller_dict})
                product_dict["base_product_item_id"] = row.base_product_item_id

                product_item_dict = {}
                product_item_dict["id"] = row.product_item_id
                product_item_dict["product_id"] = row.pi_product_id
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
                product_item_dict.update(
                    json.loads(json.dumps({"added_at": row.pi_added_at}, default=str))
                )
                product_item_dict.update(
                    json.loads(
                        json.dumps({"updated_at": row.pi_updated_at}, default=str)
                    )
                )
                product_item_dict["product_item_status"] = row.product_item_status

                product_item_dict["variant"] = row.variant
                product_item_dict["variant_value"] = row.variant_value

                average_rating, rating_count = get_avg_ratings_and_count(
                    cursor, product_dict["id"]
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
                WHERE m.id = (
                    SELECT pim.media_id From product_item_medias pim
                    WHERE pim.product_item_id = %s 
                    ORDER BY pim.display_order LIMIT 1
                )"""
                cursor.execute(GET_BASE_MEDIA, (product_item_dict["id"],))
                row = cursor.fetchone()
                if row is None:
                    app.logger.debug("No media rows")
                    product_item_dict.update({"media": media_dict})
                    product_dict.update({"base_product_item": product_item_dict})
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
                product_item_dict.update({"media": media_dict})
                product_dict.update({"base_product_item": product_item_dict})
                products_list.append(product_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, "Bad Request")
        finally:
            cursor.close()
        # app.logger.debug(products_list)
        return products_list
