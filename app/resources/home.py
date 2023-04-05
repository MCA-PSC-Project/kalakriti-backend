from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Home(Resource):
    def get(self):
        pass


class RecommendedProducts(Resource):
    def get(self):
        pass


class PopularProducts(Resource):
    def get(self):
        pass


class NewProducts(Resource):
    def get(self):
        args = request.args  # retrieve args from query string
        product_status = args.get('product_status', None)
        if not product_status:
            product_status = 'published'
            try:
                response = app_globals.redis_client.get('new_products_list')
                if response:
                    return json.loads(response.decode('utf-8'))
            except Exception as err:
                app.logger.debug(err)

        limit = args.get('limit', None)
        if not limit:
            limit = 10
        try:
            cursor = app_globals.get_named_tuple_cursor()
            GET_NEW_PRODUCTS = '''SELECT p.id AS product_id, p.product_name, p.product_description, 
            p.currency, p.product_status, p.min_order_quantity, p.max_order_quantity,
            p.added_at, p.updated_at, 
            s.id AS seller_id, s.seller_name, s.email,
            pbi.product_item_id AS base_product_item_id
            FROM products p 
            JOIN sellers s ON p.seller_id = s.id 
            JOIN product_base_item pbi ON p.id = pbi.product_id
            WHERE p.product_status = %s 
            ORDER BY p.id DESC 
            LIMIT %s'''

            cursor.execute(GET_NEW_PRODUCTS, (product_status, limit,))
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

                product_item_status = product_status
                GET_PRODUCT_BASE_ITEM = '''SELECT pi.id AS product_item_id, pi.product_id, pi.product_variant_name, pi."SKU",
                pi.original_price, pi.offer_price, pi.quantity_in_stock, pi.added_at, pi.updated_at, pi.product_item_status,
                (SELECT v.variant AS variant FROM variants v WHERE v.id = 
                (SELECT vv.variant_id FROM variant_values vv WHERE vv.id = piv.variant_value_id)),
                (SELECT vv.variant_value AS variant_value FROM variant_values vv WHERE vv.id = piv.variant_value_id)
                FROM product_items pi 
                JOIN product_item_values piv ON pi.id = piv.product_item_id
                WHERE pi.id= %s AND pi.product_item_status = %s '''

                base_product_item_dict = {}
                cursor.execute(GET_PRODUCT_BASE_ITEM,
                               (product_dict['base_product_item_id'], product_item_status,))
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
                base_product_item_dict['product_item_status'] = row.product_item_status

                base_product_item_dict['variant'] = row.variant
                base_product_item_dict['variant_value'] = row.variant_value

                media_dict = {}
                GET_BASE_MEDIA = '''SELECT m.id AS media_id, m.name, m.path
                FROM media m
                WHERE m.id = (SELECT pim.media_id From product_item_medias pim
                WHERE pim.product_item_id = %s 
                ORDER BY pim.display_order LIMIT 1) '''
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
                # media_dict['path'] = row.pathp
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
        if product_status == 'published':
            app_globals.redis_client.set(
                'new_products_list', json.dumps(products_list))
            app_globals.redis_client.expire('new_products_list', 60)  # seconds
        return products_list
