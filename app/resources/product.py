from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Products(Resource):
    # todo: work on medias and tags
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
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
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            CREATE_PRODUCT = '''INSERT INTO products(product_name, product_description, category_id, subcategory_id, 
            currency, seller_user_id, added_at) 
            VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id'''
            cursor.execute(CREATE_PRODUCT,
                           (product_dict.get('product_name'), product_dict.get(
                               'product_description'),
                            product_dict.get('category_id'), product_dict.get(
                               'subcategory_id'),
                            product_dict.get('currency', 'INR'),
                            user_id, current_time,))
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

    def get(self, product_id):
        product_dict = {}

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)
            GET_PRODUCT = '''SELECT p.id, p.product_name, p.product_description, 
        ct.id, ct.name,
        sct.id, sct.name, sct.parent_id, 
        p.currency, p.product_status,
        p.added_at, p.updated_at, 
        u.id, u.first_name, u.last_name, u.email 
        FROM products p 
        JOIN categories ct ON p.category_id = ct.id
        LEFT JOIN categories sct ON p.subcategory_id = sct.id
        JOIN users u ON p.seller_user_id = u.id 
        WHERE p.id= %s'''

            cursor.execute(GET_PRODUCT, (product_id,))
            row = cursor.fetchone()
            if row is None:
                abort(400, 'Bad Request')
            product_dict['id'] = row[0]
            product_dict['product_name'] = row[1]
            product_dict['product_description'] = row[2]

            category_dict = {}
            category_dict['id'] = row[3]
            category_dict['name'] = row[4]
            product_dict.update({"category": category_dict})

            subcategory_dict = {}
            subcategory_dict['id'] = row[5]
            subcategory_dict['name'] = row[6]
            subcategory_dict['parent_id'] = row[7]
            product_dict.update({"subcategory": subcategory_dict})

            product_dict['currency'] = row[8]
            product_dict['product_status'] = row[9]
            # product_dict['added_at'] = row[9].isoformat()
            product_dict.update(json.loads(
                json.dumps({'added_at': row[10]}, default=str)))
            # product_dict['updated_at'] = row[10].isoformat()
            product_dict.update(json.loads(
                json.dumps({'updated_at': row[11]}, default=str)))

            seller_dict = {}
            seller_dict['id'] = row[12]
            seller_dict['first_name'] = row[13]
            seller_dict['last_name'] = row[14]
            seller_dict['email'] = row[15]
            product_dict.update({"seller": seller_dict})

            product_items = []
            GET_PRODUCT_ITEMS = '''SELECT pi.id, pi.product_id, pi.product_variant_name, pi."SKU", 
            pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at,
            (SELECT v.variant FROM variants v WHERE v.id = 
            (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
            (SELECT vv.variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id),
            FROM product_items pi 
            JOIN product_item_values piv ON pi.id = piv.product_item_id
            WHERE pi.product_id=%s
            '''
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(product_dict)
        return product_dict

    @ f_jwt.jwt_required()
    def put(self, category_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("category_id= %s", category_id)
        data = request.get_json()
        category_dict = json.loads(json.dumps(data))
        app.logger.debug(category_dict)

        current_time = datetime.now()

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "super-admins and admins can create categories only")

        UPDATE_CATEGORY = 'UPDATE categories SET name= %s, parent_id= %s, cover_id=%s, updated_at= %s WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_CATEGORY, (category_dict['name'], category_dict['parent_id'], category_dict['cover_id'],
                                  current_time, category_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"category_id {category_id} modified."}, 200

    @ f_jwt.jwt_required()
    def delete(self, category_id):
        # user_id = f_jwt.get_jwt_identity()
        # user_id=20
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("category_id=%s", category_id)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "super-admins and admins can create categories only")

        DELETE_CATEGORY = 'DELETE FROM categories WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            app.logger.debug("cursor object: %s", cursor, "\n")

            cursor.execute(DELETE_CATEGORY, (category_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200
