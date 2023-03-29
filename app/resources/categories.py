from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Categories(Resource):
    @f_jwt.jwt_required()
    def post(self):
        admin_id = f_jwt.get_jwt_identity()
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        data = request.get_json()
        name = data.get("name", None)
        cover_id = data.get("cover_id", None)
        parent_id = data.get("parent_id", None)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, 'Forbidden: only super-admins and admins can create category')

        CREATE_CATEGORY = '''INSERT INTO categories(name, added_at, cover_id, parent_id, added_by)
        VALUES(%s,%s, %s, %s, %s) RETURNING id'''
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(CREATE_CATEGORY, (name, datetime.now(),
                           cover_id, parent_id, admin_id))
            id = cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return f"category_id = {id} created sucessfully", 201

    def get(self):
        categories_list = []
        GET_CATEGORIES = '''SELECT c.id AS category_id, c.name AS category_name, c.parent_id,
        m.id AS media_id, m.name AS media_name, m.path
		FROM categories c
        LEFT JOIN media m ON m.id= cover_id
		WHERE c.parent_id IS NULL
		ORDER BY c.id DESC'''

        try:
            cursor = app_globals.get_named_tuple_cursor()
            cursor.execute(GET_CATEGORIES)
            rows = cursor.fetchall()
            if not rows:
                return []
            for row in rows:
                category_dict = {}
                category_dict['id'] = row.category_id
                category_dict['name'] = row.category_name
                category_dict['parent_id'] = row.parent_id
                cover_media_dict = {}
                cover_media_dict['id'] = row.media_id
                cover_media_dict['name'] = row.media_name
                path = row.path
                if path is not None:
                    cover_media_dict['path'] = "{}/{}".format(
                        app.config["S3_LOCATION"], path)
                else:
                    cover_media_dict['path'] = None
                category_dict.update({"cover": cover_media_dict})
                categories_list.append(category_dict)

            for i in range(0, len(categories_list)):
                subcategories_list = []
                GET_SUBCATEGORIES = '''SELECT c.id AS category_id, c.name AS category_name, c.parent_id,
                m.id AS media_id, m.name AS media_name, m.path
                FROM categories c
                LEFT JOIN media m on c.cover_id = m.id
                WHERE c.parent_id = %s ORDER BY c.id'''

                try:
                    cursor = app_globals.get_named_tuple_cursor()
                    cursor.execute(GET_SUBCATEGORIES,
                                   (str(categories_list[i]['id']),))
                    rows = cursor.fetchall()
                    if not rows:
                        continue
                    for row in rows:
                        subcategory_dict = {}
                        cover_media_dict = {}
                        subcategory_dict['id'] = row.category_id
                        subcategory_dict['name'] = row.category_name
                        subcategory_dict['parent_id'] = row.parent_id

                        cover_media_dict['id'] = row.media_id
                        cover_media_dict['name'] = row.media_name
                        path = row.path
                        if path is not None:
                            cover_media_dict['path'] = "{}/{}".format(
                                app.config["S3_LOCATION"], path)
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
            cursor.close()
        # app.logger.debug(categories_list)
        return categories_list

    @ f_jwt.jwt_required()
    def put(self, category_id):
        admin_id = f_jwt.get_jwt_identity()
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        app.logger.debug("category_id= %s", category_id)
        data = request.get_json()
        category_dict = json.loads(json.dumps(data))
        app.logger.debug(category_dict)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, 'Forbidden: only super-admins and admins can create category')

        UPDATE_CATEGORY = 'UPDATE categories SET name= %s, parent_id= %s, cover_id= %s, updated_at= %s WHERE id= %s'

        try:
            cursor = app_globals.get_cursor()
            cursor.execute(
                UPDATE_CATEGORY, (category_dict['name'], category_dict['parent_id'], category_dict['cover_id'],
                                  datetime.now(), category_id,))
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
        admin_id = f_jwt.get_jwt_identity()
        app.logger.debug("admin_id= %s", admin_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)

        if user_type != "admin" and user_type != "super_admin":
            abort(403, 'Forbidden: only super-admins and admins can delete category')

        try:
            cursor = app_globals.get_cursor()
            # for deleting a category only when no product is referencing it 
            # COUNT_CATEGORY_REFERENCES='''SELECT COUNT(id) FROM products WHERE category_id= %s'''
            # cursor.execute(COUNT_CATEGORY_REFERENCES, (category_id,))
            # count=cursor.fetchone()[0]

            # if count > 0:
            #     abort(400, "some products are using this category id")
            DELETE_CATEGORY = 'DELETE FROM categories WHERE id= %s'
            cursor.execute(DELETE_CATEGORY, (category_id,))
            if cursor.rowcount != 1:
                abort(400, 'Bad Request: delete row error')
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
            # app.logger.debug('cursor closed')
        return 200
