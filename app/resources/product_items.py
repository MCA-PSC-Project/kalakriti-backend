from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class ProductItems(Resource):
    def get(self, product_item_id):
        product_item_dict = {}
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            GET_PRODUCT_ITEM = '''SELECT pi.id, pi.product_id, pi.product_variant_name, pi."SKU", 
            pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at,
            (SELECT v.variant AS variant FROM variants v WHERE v.id = 
            (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
            (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
            FROM product_items pi 
            JOIN product_item_values piv ON pi.id = piv.product_item_id
            WHERE pi.id=%s
            '''

            cursor.execute(GET_PRODUCT_ITEM, (product_item_id,))
            row = cursor.fetchone()
            if not row:
                app.logger.debug("No row")
                return {}

            product_item_dict = {}
            product_item_dict['id'] = row[0]
            product_item_dict['product_id'] = row[1]
            product_item_dict['product_variant_name'] = row[2]
            product_item_dict['SKU'] = row[3]

            product_item_dict.update(json.loads(
                json.dumps({'original_price': row[4]}, default=str)))
            product_item_dict.update(json.loads(
                json.dumps({'offer_price': row[5]}, default=str)))

            product_item_dict['quantity_in_stock'] = row[6]
            product_item_dict.update(json.loads(
                json.dumps({'added_at': row[7]}, default=str)))
            product_item_dict.update(json.loads(
                json.dumps({'updated_at': row[8]}, default=str)))

            product_item_dict['variant'] = row[9]
            product_item_dict['variant_value'] = row[10]

            # GET_MEDIAS='''SELECT m.id, m.name, m.path, pim.display_order
            # FROM media m WHERE m.id IN
            # (SELECT pim.media_id, pim.display_order FROM product_item_medias pim
            # WHERE pim.product_item_id= %s)
            # '''

            GET_MEDIAS = '''SELECT m.id, m.name, m.path, pim.display_order, pim.media_id
            FROM product_item_medias pim 
            JOIN LATERAL
            (SELECT m.id, m.name, m.path 
            FROM media m 
            WHERE m.id = pim.media_id
            ) AS m ON TRUE
            WHERE pim.product_item_id= %s
            ORDER BY pim.display_order'''

            media_list = []
            cursor.execute(GET_MEDIAS, (product_item_id,))
            rows = cursor.fetchall()
            if not rows:
                # app.logger.debug("No media rows")
                pass
            for row in rows:
                media_dict = {}
                media_dict['id'] = row[0]
                media_dict['name'] = row[1]
                # media_dict['path'] = row[2]
                path = row[2]
                if path is not None:
                    media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], row[2])
                else:
                    media_dict['path'] = None
                media_dict['pim_display_order'] = row[3]
                media_dict['pim_media_id'] = row[4]
                media_list.append(media_dict)
            product_item_dict.update({"medias": media_list})

        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(product_dict)
        return product_item_dict


class SellersProductItems(Resource):
    # todo: work on medias and tags
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        product_item_dict = json.loads(json.dumps(data))
        current_time = datetime.now()

        if user_type != 'seller':
            abort(400, "only sellers can create product-items")

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        # print(app_globals.db_conn)
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

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
                           (product_item_dict.get('product_id'), product_item_dict.get('product_variant_name'),
                            product_item_dict.get('SKU'),
                            product_item_dict.get('original_price'), product_item_dict.get(
                               'offer_price'),
                            product_item_dict.get('quantity_in_stock'), current_time))
            product_item_id = cursor.fetchone()[0]

            ASSOCIATE_PRODUCT_ITEM_WITH_VARIANT = '''INSERT INTO product_item_values(product_item_id, variant_value_id)
            VALUES(%s, %s)'''
            cursor.execute(ASSOCIATE_PRODUCT_ITEM_WITH_VARIANT,
                           (product_item_id, variant_value_id,))
            # product_item_value_id = cursor.fetchone()[0]

            INSERT_MEDIAS = '''INSERT INTO product_item_medias(media_id, product_item_id, display_order)
            VALUES(%s, %s, %s)'''

            media_id_list = product_item_dict.get("media_ids")
            values_tuple_list = []
            for media_id_dict in media_id_list:
                values_tuple = (media_id_dict.get(
                    "media_id"), product_item_id, media_id_dict.get("display_order"))
                values_tuple_list.append(values_tuple)
            app.logger.debug("values_tuple_list= %s", values_tuple_list)

            psycopg2.extras.execute_batch(
                cursor, INSERT_MEDIAS, values_tuple_list)
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
        return f"product_item_id = {product_item_id} created in product_id = {product_item_dict.get('product_id')} successfully", 201

    # to be worked or discarded
    @f_jwt.jwt_required()
    def get(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
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

        products_list = []

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)
            GET_PRODUCTS = '''SELECT p.id, p.product_name, p.product_description, 
            ct.id, ct.name,
            sct.id, sct.name, sct.parent_id, 
            p.currency, p.product_status,
            p.added_at, p.updated_at, 
            u.id, u.first_name, u.last_name, u.email,
            pbi.product_item_id
            FROM products p 
            JOIN categories ct ON p.category_id = ct.id
            LEFT JOIN categories sct ON p.subcategory_id = sct.id
            JOIN users u ON p.seller_user_id = u.id 
            JOIN product_base_item pbi ON p.id = pbi.product_id
            WHERE p.seller_user_id= %s 
            ORDER BY p.id DESC'''

            cursor.execute(GET_PRODUCTS, (seller_user_id,))
            rows = cursor.fetchall()

            for row in rows:
                product_dict = {}

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
                product_dict.update(json.loads(
                    json.dumps({'added_at': row[10]}, default=str)))
                product_dict.update(json.loads(
                    json.dumps({'updated_at': row[11]}, default=str)))

                seller_dict = {}
                seller_dict['id'] = row[12]
                seller_dict['first_name'] = row[13]
                seller_dict['last_name'] = row[14]
                seller_dict['email'] = row[15]
                product_dict.update({"seller": seller_dict})

                product_dict['base_product_item_id'] = row[16]
                products_list.append(product_dict)

                # for items list
                product_items_list = []
                GET_PRODUCT_ITEMS = '''SELECT pi.id, pi.product_id, pi.product_variant_name, pi."SKU",
                pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at,
                (SELECT v.variant AS variant FROM variants v WHERE v.id =
                (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
                (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
                FROM product_items pi
                JOIN product_item_values piv ON pi.id = piv.product_item_id
                WHERE pi.product_id=%s
                ORDER BY pi.id
                '''

                cursor.execute(GET_PRODUCT_ITEMS, (product_dict.get('id'),))
                rows = cursor.fetchall()
                if not rows:
                    app.logger.debug("No rows")
                    return product_dict
                for row in rows:
                    product_item_dict = {}
                    product_item_dict['id'] = row[0]
                    product_item_dict['product_id'] = row[1]
                    product_item_dict['product_variant_name'] = row[2]
                    product_item_dict['SKU'] = row[3]

                    product_item_dict.update(json.loads(
                        json.dumps({'original_price': row[4]}, default=str)))
                    product_item_dict.update(json.loads(
                        json.dumps({'offer_price': row[5]}, default=str)))

                    product_item_dict['quantity_in_stock'] = row[6]
                    product_item_dict.update(json.loads(
                        json.dumps({'added_at': row[7]}, default=str)))
                    product_item_dict.update(json.loads(
                        json.dumps({'updated_at': row[8]}, default=str)))

                    product_item_dict['variant'] = row[9]
                    product_item_dict['variant_value'] = row[10]

                    product_items_list.append(product_item_dict)

                product_dict.update({'product_items': product_items_list})
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(product_dict)
        return products_list

    @ f_jwt.jwt_required()
    def put(self, product_item_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("product_item_id= %s", product_item_id)
        data = request.get_json()
        product_item_dict = json.loads(json.dumps(data))
        # app.logger.debug(product_dict)

        current_time = datetime.now()

        if user_type != "seller" and user_type != "admin" and user_type != "super_admin":
            abort(400, "only seller, super-admins and admins can update product-item")

        # before beginning transaction autocommit must be off
        app_globals.db_conn.autocommit = False
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            GET_VARIANT_VALUE_ID = '''SELECT variant_value_id FROM product_item_values WHERE product_item_id= %s'''
            cursor.execute(
                GET_VARIANT_VALUE_ID, (str(product_item_id),))
            row = cursor.fetchone()
            if not row:
                # app.logger.debug("variant_value_id not found!")
                # abort(400, 'variant_value_id not found!')
                raise Exception('variant_value_id not found!')
            variant_value_id = row[0]

            # check correct variant is passed from user
            GET_VARIANT_ID = '''SELECT id FROM variants WHERE variant= %s'''
            cursor.execute(
                GET_VARIANT_ID, (product_item_dict.get('variant').upper(),))
            row = cursor.fetchone()
            if not row:
                # app.logger.debug("variant_id not found!")
                # abort(400, 'variant_id not found!')
                raise Exception('variant_id not found!')
            variant_id = row[0]

            UPDATE_VARIANT_VALUE = '''UPDATE variant_values SET variant_id= %s, variant_value= %s
            WHERE id= %s'''

            cursor.execute(UPDATE_VARIANT_VALUE, (variant_id, product_item_dict.get(
                'variant_value'), variant_value_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update variant_values row error')

            UPDATE_PRODUCT_ITEM = '''UPDATE product_items SET product_variant_name= %s, 
            "SKU"= %s, original_price= %s, offer_price= %s, quantity_in_stock= %s, updated_at= %s 
            WHERE id= %s'''

            cursor.execute(
                UPDATE_PRODUCT_ITEM, (product_item_dict.get('product_variant_name'), product_item_dict.get('SKU'),
                                      product_item_dict.get(
                                          'original_price'), product_item_dict.get('offer_price'),
                                      product_item_dict.get('quantity_in_stock'), current_time, str(product_item_id),))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update product_items row error')
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
        return {"message": f"product_item_id {product_item_id} modified."}, 200

    # mark/unmark product item as trashed (partially delete)
    # todo: check product_item_id is not base item
    @ f_jwt.jwt_required()
    def patch(self, product_item_id):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("product_item_id= %s", product_item_id)
        data = request.get_json()

        if 'product_item_status' in data.keys():
            if user_type != "admin" and user_type != "super_admin":
                abort(
                    400, "only super-admins and admins are allowed to update product_item status")
            value = data['product_item_status']
            # app.logger.debug("product_status= %s", value)
            UPDATE_PRODUCT_ITEM_STATUS = '''UPDATE product_items SET product_item_status= %s, updated_at= %s
            WHERE id= %s'''
            PATCH_PRODUCT_ITEM = UPDATE_PRODUCT_ITEM_STATUS
        elif 'trashed' in data.keys():
            if user_type != "seller" and user_type != "admin" and user_type != "super_admin":
                abort(
                    400, "only seller, super-admins and admins can trash a product_item")
            value = data['trashed']
            # app.logger.debug("trashed= %s", value)
            UPDATE_PRODUCT_ITEM_TRASHED_VALUE = '''UPDATE product_items SET trashed= %s, updated_at= %s
            WHERE id= %s'''
            PATCH_PRODUCT_ITEM = UPDATE_PRODUCT_ITEM_TRASHED_VALUE
        else:
            abort(400, "Bad Request")
        current_time = datetime.now()

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                PATCH_PRODUCT_ITEM, (value, current_time, product_item_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: update row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"product_item_id {product_item_id} modified."}, 200

    # delete trashed product item
    # todo: check product_item_id is not base item
    @ f_jwt.jwt_required()
    def delete(self, product_item_id):
        # user_id = f_jwt.get_jwt_identity()
        # user_id=20
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("product_id=%s", product_item_id)

        if user_type != "admin" and user_type != "super_admin":
            abort(400, "only super-admins and admins can delete product item")

        DELETE_TRASHED_PRODUCT_ITEM = 'DELETE FROM product_items WHERE id= %s AND trashed= true'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(DELETE_TRASHED_PRODUCT_ITEM, (product_item_id,))
            # app.logger.debug("row_counts= %s", cursor.rowcount)
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 200
