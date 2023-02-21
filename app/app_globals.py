import psycopg2
from flask import current_app as app

global db_conn_pool
global db_conn
global mail
global s3


def get_cursor():
    # cursor = db_conn.cursor()
    global db_conn_pool
    global db_conn
    try:
        # app.logger.debug(db_conn)
        cursor = db_conn.cursor()
        # raise Exception
    except (Exception, psycopg2.Error) as err:
        # db_conn.close()
        # app.logger.debug("db_conn.closed: %s", db_conn.closed)
        if db_conn.closed:
            db_conn = db_conn_pool.getconn()
            if db_conn == None:
                app.logger.fatal('Database connection error')
            db_conn.autocommit = True
            # app.logger.debug(db_conn)
            cursor = db_conn.cursor()
    return cursor