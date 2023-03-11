from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class ProductsByCategory(Resource):
    def get(self):
        args = request.args  # retrieve args from query string
        category_id = args.get('category_id', None)
        subcategory_id = args.get('subcategory_id', None)

        if not category_id and not subcategory_id:
            abort(400, 'Bad Request.Provide either category_id or subcategory_id')
        elif not category_id:
            app.logger.debug("?subcategory_id=%s", subcategory_id)
            category_id = subcategory_id
            column_name = 'p.subcategory_id'
        elif not subcategory_id:
            app.logger.debug("?category_id=%s", category_id)
            column_name = 'p.category_id'
        else:
            abort(400, 'Bad Request')

        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_PRODUCTS_BY_CATEGORY = '''SELECT p.id AS product_id, p.product_name, p.product_description, 
            p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
            p.added_at, p.updated_at, 
            s.id AS seller_id, s.seller_name, s.email,
            pbi.product_item_id AS base_product_item_id
            FROM products p 
            JOIN sellers s ON p.seller_id = s.id 
            JOIN product_base_item pbi ON p.id = pbi.product_id
            WHERE {} IN (SELECT id FROM categories ct WHERE ct.id = %s)
            ORDER BY p.id DESC'''.format(column_name)

            cursor.execute(GET_PRODUCTS_BY_CATEGORY, (category_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            products_list = []
            for row in rows:
                product_dict = {}
                product_dict['id'] = row.product_id
                product_dict['product_name'] = row.product_name
                product_dict['product_description'] = row.product_description
                product_dict['currency'] = row.currency
                product_dict['product_status'] = row.product_status
                product_dict['min_order_quantity'] = row.min_order_quantity
                product_dict['max_order_quantity'] = row.max_order_quantity
                product_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                product_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))

                seller_dict = {}
                seller_dict['id'] = row.seller_id
                seller_dict['seller_name'] = row.seller_name
                seller_dict['email'] = row.email
                product_dict.update({"seller": seller_dict})

                product_dict['base_product_item_id'] = row.base_product_item_id

                GET_PRODUCT_BASE_ITEM = '''SELECT pi.id AS product_item_id, pi.product_id, pi.product_variant_name, pi."SKU",
                pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at,
                (SELECT v.variant AS variant FROM variants v WHERE v.id = 
                (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
                (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
                FROM product_items pi 
                JOIN product_item_values piv ON pi.id = piv.product_item_id
                WHERE pi.id= %s
                '''

                base_product_item_dict = {}
                cursor.execute(GET_PRODUCT_BASE_ITEM,
                               (product_dict['base_product_item_id'],))
                row = cursor.fetchone()
                if not row:
                    app.logger.debug("No base product item row")
                    product_dict.update(
                        {"base_product_item": base_product_item_dict})
                    products_list.append(product_dict)
                    continue
                base_product_item_dict['id'] = row.product_item_id
                base_product_item_dict['product_id'] = row.product_id
                base_product_item_dict['product_variant_name'] = row.product_variant_name
                base_product_item_dict['SKU'] = row.SKU

                base_product_item_dict.update(json.loads(
                    json.dumps({'original_price': row.original_price}, default=str)))
                base_product_item_dict.update(json.loads(
                    json.dumps({'offer_price': row.offer_price}, default=str)))

                base_product_item_dict['quantity_in_stock'] = row.quantity_in_stock
                base_product_item_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                base_product_item_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))

                base_product_item_dict['variant'] = row.variant
                base_product_item_dict['variant_value'] = row.variant_value

                media_dict = {}
                GET_BASE_MEDIA = '''SELECT m.id AS media_id, m.name, m.path
                FROM media m
                WHERE m.id = (SELECT pim.media_id From product_item_medias pim
                WHERE pim.product_item_id = %s 
                ORDER BY pim.display_order LIMIT 1) 
                '''
                cursor.execute(
                    GET_BASE_MEDIA, (product_dict['base_product_item_id'],))
                row = cursor.fetchone()
                if row is None:
                    app.logger.debug("No media rows")
                    base_product_item_dict.update({"media": media_dict})
                    product_dict.update(
                        {"base_product_item": base_product_item_dict})
                    products_list.append(product_dict)
                    continue
                media_dict['id'] = row.media_id
                media_dict['name'] = row.name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    media_dict['path'] = None
                base_product_item_dict.update({"media": media_dict})
                product_dict.update(
                    {"base_product_item": base_product_item_dict})
                products_list.append(product_dict)

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(products_list)
        return products_list


class Products(Resource):
    def get(self, product_id):
        product_dict = {}
        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_PRODUCT = '''SELECT p.id AS product_id, p.product_name, p.product_description, 
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
            WHERE p.id= %s'''

            cursor.execute(GET_PRODUCT, (product_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            product_dict['id'] = row.product_id
            product_dict['product_name'] = row.product_name
            product_dict['product_description'] = row.product_description

            category_dict = {}
            category_dict['id'] = row.category_id
            category_dict['name'] = row.category_name
            product_dict.update({"category": category_dict})

            subcategory_dict = {}
            subcategory_dict['id'] = row.subcategory_id
            subcategory_dict['name'] = row.subcategory_name
            subcategory_dict['parent_id'] = row.parent_id
            product_dict.update({"subcategory": subcategory_dict})

            product_dict['currency'] = row.currency
            product_dict['product_status'] = row.product_status
            product_dict['min_order_quantity'] = row.min_order_quantity
            product_dict['max_order_quantity'] = row.max_order_quantity

            product_dict.update(json.loads(
                json.dumps({'added_at': row.added_at}, default=str)))
            product_dict.update(json.loads(
                json.dumps({'updated_at': row.updated_at}, default=str)))

            seller_dict = {}
            seller_dict['id'] = row.seller_id
            seller_dict['seller_name'] = row.seller_name
            seller_dict['email'] = row.email
            product_dict.update({"seller": seller_dict})

            product_dict['base_product_item_id'] = row.base_product_item_id

            product_items_list = []
            GET_PRODUCT_ITEMS = '''SELECT pi.id AS product_item_id, pi.product_id, pi.product_variant_name, pi."SKU", 
            pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at,
            (SELECT v.variant AS variant FROM variants v WHERE v.id = 
            (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
            (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
            FROM product_items pi 
            JOIN product_item_values piv ON pi.id = piv.product_item_id
            WHERE pi.product_id=%s
            ORDER BY pi.id
            '''

            cursor.execute(GET_PRODUCT_ITEMS, (product_id,))
            rows = cursor.fetchall()
            if not rows:
                app.logger.debug("No rows")
                return product_dict
            for row in rows:
                product_item_dict = {}
                product_item_dict['id'] = row.product_item_id
                product_item_dict['product_id'] = row.product_id
                product_item_dict['product_variant_name'] = row.product_variant_name
                product_item_dict['SKU'] = row.SKU

                product_item_dict.update(json.loads(
                    json.dumps({'original_price': row.original_price}, default=str)))
                product_item_dict.update(json.loads(
                    json.dumps({'offer_price': row.offer_price}, default=str)))

                product_item_dict['quantity_in_stock'] = row.quantity_in_stock
                product_item_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                product_item_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))

                product_item_dict['variant'] = row.variant
                product_item_dict['variant_value'] = row.variant_value

                if product_item_dict['id'] == product_dict['base_product_item_id']:
                    GET_MEDIAS = '''SELECT m.id AS media_id, m.name, m.path, pim.display_order
                    FROM product_item_medias pim 
                    JOIN LATERAL
                    (SELECT m.id, m.name, m.path 
                    FROM media m 
                    WHERE m.id = pim.media_id
                    ) AS m ON TRUE
                    WHERE pim.product_item_id= %s
                    ORDER BY pim.display_order'''

                    media_list = []
                    cursor.execute(
                        GET_MEDIAS, (product_dict['base_product_item_id'],))
                    rows = cursor.fetchall()
                    if not rows:
                        # app.logger.debug("No media rows")
                        pass
                    for row in rows:
                        media_dict = {}
                        media_dict['id'] = row.media_id
                        media_dict['name'] = row.name
                        # media_dict['path'] = row[2]
                        path = row.path
                        if path is not None:
                            media_dict['path'] = "{}/{}".format(
                                app.config["S3_LOCATION"], path)
                        else:
                            media_dict['path'] = None
                        media_dict['display_order'] = row.display_order
                        media_list.append(media_dict)
                    product_item_dict.update({"medias": media_list})

                product_items_list.append(product_item_dict)
            product_dict.update({'product_items': product_items_list})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(product_dict)
        return product_dict


class SellersProducts(Resource):
    # todo: work on medias and tags
    @f_jwt.jwt_required()
    def post(self):
        seller_id = f_jwt.get_jwt_identity()
        app.logger.debug("seller_id= %s", seller_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        product_dict = json.loads(json.dumps(data))
        product_item_dict = product_dict['product_items'][0]
        current_time = datetime.now()

        if user_type != 'seller':
            abort(400, "only sellers can create products")

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        # print(app_globals.db_conn)
        try:
            cursor = app_globals.get_cursor()
            CREATE_PRODUCT = '''INSERT INTO products(product_name, product_description, category_id, subcategory_id, 
            currency, seller_id, min_order_quantity, max_order_quantity, added_at) 
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id'''
            cursor.execute(CREATE_PRODUCT,
                           (product_dict.get('product_name'), product_dict.get('product_description'),
                            product_dict.get('category_id'), product_dict.get(
                                'subcategory_id'),
                            product_dict.get('currency', 'INR'), seller_id,
                            product_dict.get('min_order_quantity'), product_dict.get(
                                'max_order_quantity'),
                            current_time,))
            product_id = cursor.fetchone()[0]

            GET_VARIANT_ID = '''SELECT id FROM variants WHERE variant= %s'''
            cursor.execute(
                GET_VARIANT_ID, (product_item_dict.get('variant').upper(),))
            row = cursor.fetchone()
            if not row:
                app.logger.debug("variant_id not found!")
                app_globals.db_conn.rollback()
            variant_id = row[0]

            CREATE_VARIANT_VALUE = '''INSERT INTO variant_values(variant_id, variant_value) VALUES(%s, %s) RETURNING id'''
            cursor.execute(CREATE_VARIANT_VALUE,
                           (variant_id, product_item_dict.get('variant_value'),))
            variant_value_id = cursor.fetchone()[0]

            CREATE_PRODUCT_ITEM = '''INSERT INTO product_items(product_id, product_variant_name, "SKU",
            original_price, offer_price, quantity_in_stock, added_at)
            VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id'''
            cursor.execute(CREATE_PRODUCT_ITEM,
                           (product_id, product_item_dict.get('product_variant_name'), product_item_dict.get('SKU'),
                            product_item_dict.get('original_price'), product_item_dict.get(
                               'offer_price'),
                            product_item_dict.get('quantity_in_stock'), current_time))
            product_item_id = cursor.fetchone()[0]

            ASSOCIATE_PRODUCT_ITEM_WITH_VARIANT = '''INSERT INTO product_item_values(product_item_id, variant_value_id)
            VALUES(%s, %s)'''
            cursor.execute(ASSOCIATE_PRODUCT_ITEM_WITH_VARIANT,
                           (product_item_id, variant_value_id,))
            # product_item_value_id = cursor.fetchone()[0]

            ASSOCIATE_PRODUCT_WITH_BASE_ITEM = '''INSERT INTO product_base_item(product_id, product_item_id)
            VALUES(%s, %s)'''
            cursor.execute(ASSOCIATE_PRODUCT_WITH_BASE_ITEM,
                           (product_id, product_item_id,))
            # product_base_item_id = cursor.fetchone()[0]

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            app_globals.db_conn.rollback()
            app_globals.db_conn.autocommit = True
            app.logger.debug("autocommit switched back from off to on")
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        app_globals.db_conn.commit()
        app_globals.db_conn.autocommit = True
        return f"product_id = {product_id} with product_item_id= {product_item_id} created successfully", 201

    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("seller_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if user_type == "seller":
            seller_user_id = user_id
        elif user_type == "admin" or user_type == "super_admin":
            args = request.args  # retrieve args from query string
            seller_user_id = args.get('seller_user_id', None)
            app.logger.debug("?seller_user_id=%s", seller_user_id)
        else:
            abort(400, "only sellers, admins and super_admins can view seller's products")

        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_PRODUCTS_BY_SELLER = '''SELECT p.id AS product_id, p.product_name, p.product_description, 
            p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
            p.added_at, p.updated_at, 
            s.id AS seller_id, s.seller_name, s.email,
            pbi.product_item_id AS base_product_item_id
            FROM products p 
            JOIN sellers s ON p.seller_id = s.id 
            JOIN product_base_item pbi ON p.id = pbi.product_id
            WHERE p.seller_id = %s
            ORDER BY p.id DESC'''

            cursor.execute(GET_PRODUCTS_BY_SELLER, (seller_user_id,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            products_list = []
            for row in rows:
                product_dict = {}
                product_dict['id'] = row.product_id
                product_dict['product_name'] = row.product_name
                product_dict['product_description'] = row.product_description
                product_dict['currency'] = row.currency
                product_dict['product_status'] = row.product_status
                product_dict['min_order_quantity'] = row.min_order_quantity
                product_dict['max_order_quantity'] = row.max_order_quantity
                product_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                product_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))

                seller_dict = {}
                seller_dict['id'] = row.seller_id
                seller_dict['seller_name'] = row.seller_name
                seller_dict['email'] = row.email
                product_dict.update({"seller": seller_dict})

                product_dict['base_product_item_id'] = row.base_product_item_id

                GET_PRODUCT_BASE_ITEM = '''SELECT pi.id AS product_item_id, pi.product_id, pi.product_variant_name, pi."SKU",
                pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at,
                (SELECT v.variant AS variant FROM variants v WHERE v.id = 
                (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
                (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
                FROM product_items pi 
                JOIN product_item_values piv ON pi.id = piv.product_item_id
                WHERE pi.id= %s
                '''

                base_product_item_dict = {}
                cursor.execute(GET_PRODUCT_BASE_ITEM,
                               (product_dict['base_product_item_id'],))
                row = cursor.fetchone()
                if not row:
                    app.logger.debug("No base product item row")
                    product_dict.update(
                        {"base_product_item": base_product_item_dict})
                    products_list.append(product_dict)
                    continue
                base_product_item_dict['id'] = row.product_item_id
                base_product_item_dict['product_id'] = row.product_id
                base_product_item_dict['product_variant_name'] = row.product_variant_name
                base_product_item_dict['SKU'] = row.SKU

                base_product_item_dict.update(json.loads(
                    json.dumps({'original_price': row.original_price}, default=str)))
                base_product_item_dict.update(json.loads(
                    json.dumps({'offer_price': row.offer_price}, default=str)))

                base_product_item_dict['quantity_in_stock'] = row.quantity_in_stock
                base_product_item_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                base_product_item_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))

                base_product_item_dict['variant'] = row.variant
                base_product_item_dict['variant_value'] = row.variant_value

                media_dict = {}
                GET_BASE_MEDIA = '''SELECT m.id AS media_id, m.name, m.path
                FROM media m
                WHERE m.id = (SELECT pim.media_id From product_item_medias pim
                WHERE pim.product_item_id = %s 
                ORDER BY pim.display_order LIMIT 1) 
                '''
                cursor.execute(
                    GET_BASE_MEDIA, (product_dict['base_product_item_id'],))
                row = cursor.fetchone()
                if row is None:
                    app.logger.debug("No media rows")
                    base_product_item_dict.update({"media": media_dict})
                    product_dict.update(
                        {"base_product_item": base_product_item_dict})
                    products_list.append(product_dict)
                    continue
                media_dict['id'] = row.media_id
                media_dict['name'] = row.name
                # media_dict['path'] = row.path
                path = row.path
                if path is not None:
                    media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    media_dict['path'] = None
                base_product_item_dict.update({"media": media_dict})
                product_dict.update(
                    {"base_product_item": base_product_item_dict})
                products_list.append(product_dict)

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(products_list)
        return products_list

    # update product only
    @ f_jwt.jwt_required()
    def put(self, product_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("product_id= %s", product_id)
        data = request.get_json()
        product_dict = json.loads(json.dumps(data))
        # app.logger.debug(product_dict)

        current_time = datetime.now()

        if user_type != "seller" and user_type != "admin" and user_type != "super_admin":
            abort(400, "only seller, super-admins and admins can update product")

        UPDATE_PRODUCT = '''UPDATE products SET product_name= %s, product_description= %s,
        category_id= %s, subcategory_id= %s, currency= %s, min_order_quantity= %s, max_order_quantity= %s,
        updated_at= %s 
        WHERE id= %s'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_PRODUCT, (product_dict.get('product_name'), product_dict.get('product_description'),
                                 product_dict.get('category_id'), product_dict.get(
                                     'subcategory_id'),
                                 product_dict.get('currency', 'INR'),
                                 product_dict.get('min_order_quantity'), product_dict.get(
                                     'max_order_quantity'),
                                 current_time, product_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"product_id {product_id} modified."}, 200

    # update product_status or mark/unmark product as trashed (partially delete)
    @ f_jwt.jwt_required()
    def patch(self, product_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("product_id= %s", product_id)
        data = request.get_json()

        if 'product_status' in data.keys():
            if user_type != "admin" and user_type != "super_admin":
                abort(
                    400, "only super-admins and admins are allowed to update product status")
            value = data['product_status']
            # app.logger.debug("product_status= %s", value)
            UPDATE_PRODUCT_STATUS = '''UPDATE products SET product_status= %s, updated_at= %s
            WHERE id= %s'''
            PATCH_PRODUCT = UPDATE_PRODUCT_STATUS
        elif 'trashed' in data.keys():
            if user_type != "seller" and user_type != "admin" and user_type != "super_admin":
                abort(400, "only seller, super-admins and admins can trash a product")
            value = data['trashed']
            # app.logger.debug("trashed= %s", value)
            UPDATE_PRODUCT_TRASHED_VALUE = '''UPDATE products SET trashed= %s, updated_at= %s
            WHERE id= %s'''
            PATCH_PRODUCT = UPDATE_PRODUCT_TRASHED_VALUE
        else:
            abort(400, "Bad Request")
        current_time = datetime.now()

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                PATCH_PRODUCT, (value, current_time, product_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"product_id {product_id} modified."}, 200

    # delete trashed product
    @ f_jwt.jwt_required()
    def delete(self, product_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("product_id=%s", product_id)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can delete product")

        app_globals.db_conn.autocommit = False
        try:
            cursor = app_globals.get_cursor()
            DELETE_VARIANT_VALUE = '''DELETE FROM variant_values vv WHERE vv.id IN (
                SELECT piv.variant_value_id FROM product_item_values piv 
                WHERE piv.product_item_id IN (
                    SELECT pi.id FROM product_items pi WHERE pi.product_id = %s
                )
            )'''

            cursor.execute(DELETE_VARIANT_VALUE, (product_id,))
            if not cursor.rowcount > 0:
                abort(400, 'Bad Request: delete variant values row error')

            DELETE_TRASHED_PRODUCT = 'DELETE FROM products WHERE id= %s AND trashed= true'
            cursor.execute(DELETE_TRASHED_PRODUCT, (product_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            app_globals.db_conn.rollback()
            app_globals.db_conn.autocommit = True
            app.logger.debug("autocommit switched back from off to on")
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        app_globals.db_conn.commit()
        app_globals.db_conn.autocommit = True
        app.logger.debug("autocommit switched back from off to on")
        return 200


class ProductsAllDetails(Resource):
    def get(self, product_id):
        product_dict = {}
        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_PRODUCT = '''SELECT p.id AS product_id, p.product_name, p.product_description, 
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
            WHERE p.id= %s'''

            cursor.execute(GET_PRODUCT, (product_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            product_dict['id'] = row.product_id
            product_dict['product_name'] = row.product_name
            product_dict['product_description'] = row.product_description

            category_dict = {}
            category_dict['id'] = row.category_id
            category_dict['name'] = row.category_name
            product_dict.update({"category": category_dict})

            subcategory_dict = {}
            subcategory_dict['id'] = row.subcategory_id
            subcategory_dict['name'] = row.subcategory_name
            subcategory_dict['parent_id'] = row.parent_id
            product_dict.update({"subcategory": subcategory_dict})

            product_dict['currency'] = row.currency
            product_dict['product_status'] = row.product_status
            product_dict['min_order_quantity'] = row.min_order_quantity
            product_dict['max_order_quantity'] = row.max_order_quantity

            product_dict.update(json.loads(
                json.dumps({'added_at': row.added_at}, default=str)))
            product_dict.update(json.loads(
                json.dumps({'updated_at': row.updated_at}, default=str)))

            seller_dict = {}
            seller_dict['id'] = row.seller_id
            seller_dict['seller_name'] = row.seller_name
            seller_dict['email'] = row.email
            product_dict.update({"seller": seller_dict})

            product_dict['base_product_item_id'] = row.base_product_item_id

            product_items_list = []
            GET_PRODUCT_ITEMS = '''SELECT pi.id AS product_item_id, pi.product_id, pi.product_variant_name, pi."SKU", 
            pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at,
            (SELECT v.variant AS variant FROM variants v WHERE v.id = 
            (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
            (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
            FROM product_items pi 
            JOIN product_item_values piv ON pi.id = piv.product_item_id
            WHERE pi.product_id=%s
            ORDER BY pi.id
            '''

            cursor.execute(GET_PRODUCT_ITEMS, (product_id,))
            rows = cursor.fetchall()
            if not rows:
                app.logger.debug("No rows")
                return product_dict
            for row in rows:
                product_item_dict = {}
                product_item_dict['id'] = row.product_item_id
                product_item_dict['product_id'] = row.product_id
                product_item_dict['product_variant_name'] = row.product_variant_name
                product_item_dict['SKU'] = row.SKU

                product_item_dict.update(json.loads(
                    json.dumps({'original_price': row.original_price}, default=str)))
                product_item_dict.update(json.loads(
                    json.dumps({'offer_price': row.offer_price}, default=str)))

                product_item_dict['quantity_in_stock'] = row.quantity_in_stock
                product_item_dict.update(json.loads(
                    json.dumps({'added_at': row.added_at}, default=str)))
                product_item_dict.update(json.loads(
                    json.dumps({'updated_at': row.updated_at}, default=str)))

                product_item_dict['variant'] = row.variant
                product_item_dict['variant_value'] = row.variant_value

                GET_MEDIAS = '''SELECT m.id AS media_id, m.name, m.path, pim.display_order, pim.media_id AS pim_media_id
                FROM product_item_medias pim 
                JOIN LATERAL
                (SELECT m.id, m.name, m.path 
                FROM media m 
                WHERE m.id = pim.media_id
                ) AS m ON TRUE
                WHERE pim.product_item_id= %s
                ORDER BY pim.display_order'''

                media_list = []
                cursor.execute(GET_MEDIAS, (product_item_dict['id'],))
                rows = cursor.fetchall()
                if not rows:
                    # app.logger.debug("No media rows")
                    pass
                for row in rows:
                    media_dict = {}
                    media_dict['id'] = row.media_id
                    media_dict['name'] = row.name
                    # media_dict['path'] = row[2]
                    path = row.path
                    if path is not None:
                        media_dict['path'] = "{}/{}".format(
                            app.config["S3_LOCATION"], path)
                    else:
                        media_dict['path'] = None
                    media_dict['display_order'] = row.display_order
                    media_dict['pim_media_id'] = row.pim_media_id
                    media_list.append(media_dict)
                product_item_dict.update({"medias": media_list})

                product_items_list.append(product_item_dict)
            product_dict.update({'product_items': product_items_list})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(product_dict)
        return product_dict
