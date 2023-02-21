from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Products(Resource):
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

        # app_globals.db_conn.autocommit = False
        print(app_globals.db_conn)
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            # cursor = app_globals.get_cursor()
            cursor = app_globals.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

            with app_globals.db_conn.transaction():
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
            app.logger.debug("cdsdssddssdcsdcscsdcsdcsdc")
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return f"product_id = {product_id} with product_item_id= {product_item_id} created sucessfully", 201

    def get(self):
        categories_list = []
        GET_CATEGORY = '''SELECT c.id, c.name, c.parent_id,
        m.id, m.name, m.path
		FROM categories c LEFT JOIN media m ON m.id= cover_id
		WHERE c.parent_id IS NULL
		ORDER BY c.id DESC'''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            # cursor = app_globals.get_cursor()
            cursor = app_globals.get_cursor()
            app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_CATEGORY)
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                category_dict = {}
                cover_media_dict = {}
                category_dict['id'] = row[0]
                category_dict['name'] = row[1]
                category_dict['parent_id'] = row[2]
                cover_media_dict['id'] = row[3]
                cover_media_dict['name'] = row[4]
                # media_dict['path'] = row[5]
                path = row[5]
                if path is not None:
                    cover_media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], row[5])
                else:
                    cover_media_dict['path'] = None
                category_dict.update({"cover": cover_media_dict})
                categories_list.append(category_dict)

            for i in range(0, len(categories_list)):
                subcategories_list = []
                GET_SUBCATEGORIES = '''SELECT c.id, c.name,c.parent_id,
                m.id, m.name, m.path
                FROM categories c LEFT JOIN media m on c.cover_id = m.id
                WHERE c.parent_id = %s ORDER BY c.id'''

                try:
                    # declare a cursor object from the connection
                    cursor = app_globals.get_cursor()
                    # app.logger.debug("cursor object: %s", cursor)
                    # app.logger.debug(categories_list[i]['id'])
                    cursor.execute(GET_SUBCATEGORIES,
                                   (str(categories_list[i]['id']),))
                    rows = cursor.fetchall()
                    if not rows:
                        continue
                    for row in rows:
                        subcategory_dict = {}
                        cover_media_dict = {}
                        subcategory_dict['id'] = row[0]
                        subcategory_dict['name'] = row[1]
                        subcategory_dict['parent_id'] = row[2]
                        cover_media_dict['id'] = row[3]
                        cover_media_dict['name'] = row[4]
                        # media_dict['path'] = row[5]
                        path = row[5]
                        if path is not None:
                            cover_media_dict['path'] = "{}/{}".format(
                                app.config["S3_LOCATION"], row[5])
                        else:
                            cover_media_dict['path'] = None
                        subcategory_dict.update({"cover": cover_media_dict})
                        subcategories_list.append(subcategory_dict)
                        categories_list[i].update(
                            {'subcategories': subcategories_list})
                except (Exception, psycopg2.Error) as err:
                    app.logger.debug(err)
                    abort(400, 'Bad Request')
                finally:
                    cursor.close()

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            # app.logger.debug("cursor closed: %s", cursor.closed)
            cursor.close()
            # app.logger.debug("cursor closed: %s", cursor.closed)
        # app.logger.debug(categories_list)
        return categories_list

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
