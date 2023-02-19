global db_conn
global mail
global s3


def get_cursor():
    cursor = db_conn.cursor()
    return cursor
