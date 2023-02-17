from datetime import datetime
import bcrypt
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.main as main
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Categories(Resource):
    @f_jwt.jwt_required()
    def post(self):
        user_id = f_jwt.get_jwt_identity()
        app.logger.debug("user_id= %s", user_id)
        claims = f_jwt.get_jwt()
        user_type = claims['user_type']
        app.logger.debug("user_type= %s", user_type)
        
        data = request.get_json()
        name = data.get("name", None)
        cover_id = data.get("cover_id", None)
        parent_id = data.get("parent_id", None)
        current_time = datetime.now()


        if user_type != "admin" and user_type != "super_admin":
            abort(400, "super-admins and admins can create categories only")

        CREATE_CATEGORY = '''INSERT INTO categories(name, added_at,cover_id,parent_id, added_by) VALUES(%s,%s, %s, %s, %s) RETURNING id'''
        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(CREATE_CATEGORY, (name, current_time, cover_id, parent_id, user_id))
            id=cursor.fetchone()[0]
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return f"category_id =  {id} created sucessfully",201

    
    # def get(self,category_id):
    #     categories_list=[]
    #     GET_CATEGORY = '''SELECT name,TO_CHAR(added_at, 'YYYY-MM-DD'), TO_CHAR(updated_at, 'YYYY-MM-DD'), added_by, cover_id
    #     FROM categories WHERE id = %s or parent_id = %s'''

    #     # catch exception for invalid SQL statement
    #     try:
    #         # declare a cursor object from the connection
    #         cursor = main.db_conn.cursor()
    #         # app.logger.debug("cursor object: %s", cursor)

    #         cursor.execute(GET_CATEGORY, (category_id,category_id,))
    #         rows = cursor.fetchall()
    #         if not rows:
    #             return {}
    #         for row in rows:
    #             categories_dict = {}
    #             categories_dict['name'] = row[0]
    #             categories_dict['added_at'] = row[1]
    #             categories_dict['updated_at'] = row[2]
    #             categories_dict['added_by'] = row[3]
    #             categories_dict['cover_id'] = row[4]
    #             # categories_dict['parent_id'] = row[5]
    #             categories_list.append(categories_dict)
    #     except (Exception, psycopg2.Error) as err:
    #         app.logger.debug(err)
    #         abort(400, 'Bad Request')
       
    #     finally:
    #         cursor.close()
    #     app.logger.debug(categories_list)
    #     return categories_list


    def get(self):
        categories_list=[]
        GET_CATEGORY = '''select c.id, c.name, c.parent_id,
        m.id, m.name, m.path 
		from categories c left join media m on m.id= cover_id 
		where c.parent_id IS NULL 
		ORDER BY c.id DESC;  '''

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(GET_CATEGORY)
            rows = cursor.fetchall()
            if not rows:
                return {}
            for row in rows:
                category_dict = {}
                media_dict = {}
                category_dict['id'] = row[0]
                category_dict['name'] = row[1]
                category_dict['parent_id'] = row[2]
                media_dict['id'] = row[3]
                media_dict['name'] = row[4]
                media_dict['path'] = row[5]
                category_dict.update({"media":media_dict})
                categories_list.append(category_dict)
            print("dddddddddddddddddddddddddd")

            for i in range(0,len(categories_list)):
                subcategories_list=[]
                GET_SUBCATEGORIES='''SELECT c.id, c.name,c.parent_id, 
                m.id, m.name, m.path
                FROM categories c LEFT JOIN media m on c.cover_id = m.id 
                WHERE c.parent_id = %s ORDER BY c.id'''

                try:
                    # declare a cursor object from the connection
                    cursor = main.db_conn.cursor()
                    # app.logger.debug("cursor object: %s", cursor)
                    print("jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj")
                    print(categories_list[i].category_dict['parent_id'])
                    cursor.execute(GET_SUBCATEGORIES,categories_list[i].category_dict['parent_id'])
                    rows = cursor.fetchall()
                    if not rows:
                        return {}
                    for row in rows:
                        subcategory_dict = {}
                        media_dict = {}
                        subcategory_dict['id'] = row[0]
                        subcategory_dict['name'] = row[1]
                        subcategory_dict['parent_id'] = row[2]
                        media_dict['id'] = row[3]
                        media_dict['name'] = row[4]
                        media_dict['path'] = row[5]
                        subcategory_dict.update({"media":media_dict})
                        subcategories_list.append(subcategory_dict)
                        categories_list[i].category_dict.update({'subcategories': subcategories_list})
                    print("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")       
                
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
        app.logger.debug(categories_list)
        return categories_list

    
    @f_jwt.jwt_required()
    def put(self,category_id):
        app.logger.debug("category_id= %s", category_id)
        data = request.get_json()
        category_dict = json.loads(json.dumps(data))
        app.logger.debug(category_dict)

        current_time = datetime.now()
        
        UPDATE_CATEGORY = 'UPDATE categories SET name= %s, parent_id= %s, cover_id=%s, updated_at= %s WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
            # app.logger.debug("cursor object: %s", cursor)

            cursor.execute(
                UPDATE_CATEGORY, (category_dict['name'], category_dict['parent_id'], category_dict['cover_id'],
                             current_time, category_id,))
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return {"message": f"category_id {category_id} modified."}, 200


    @f_jwt.jwt_required()
    def delete(self,category_id):
        #user_id = f_jwt.get_jwt_identity()
        # user_id=20
        app.logger.debug("category_id=%s", category_id)

        DELETE_CATEGORY = 'DELETE FROM categories WHERE id= %s'

        # catch exception for invalid SQL statement
        try:
            # declare a cursor object from the connection
            cursor = main.db_conn.cursor()
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
