from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Search(Resource):
    def get(self):
        args = request.args  # retrieve args from query string
        query = args.get('query', None)
        app.logger.debug("?query=%s", query)

        if not query:
            abort(400, 'Bad Request')

        # unquoted text: text not inside quote marks will be converted to terms separated by & operators, as if processed by plainto_tsquery.
        # "quoted text": text inside quote marks will be converted to terms separated by <-> operators, as if processed by phraseto_tsquery.
        # OR : the word “or” will be converted to the | operator.
        # - : a dash will be converted to the ! operator.

        query = query.replace(" ", " or ")

        GET_PRODUCTS = '''SELECT p.id, p.product_name
        FROM products p
        WHERE p.id IN (
            SELECT product_id FROM products_tsv_store 
            WHERE tsv @@ websearch_to_tsquery('english', %s)
        )'''

        products_list = []
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_PRODUCTS, (query,))
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                product_dict = {}

                product_dict['id'] = row[0]
                product_dict['product_name'] = row[1]

                products_list.append(product_dict)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(products_list)
        return products_list


class TopSearches(Resource):
    def get(self):
        GET_PRODUCTS = '''SELECT query FROM top_searches ORDER BY rank'''

        queries_list = []
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = app_globals.get_cursor()
            # # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_PRODUCTS)
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                query = row[0]
                queries_list.append(query)
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        # app.logger.debug(queries_list)
        return queries_list
