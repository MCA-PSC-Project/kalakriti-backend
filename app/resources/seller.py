def get_seller_info(cursor, product_id):
    GET_SELLER_INFO = """SELECT s.id AS seller_id, s.seller_name, s.email FROM sellers s
    WHERE s.id = (
        SELECT p.seller_id FROM products p WHERE p.id = %s
    )"""
    cursor.execute(GET_SELLER_INFO, (product_id,))
    row = cursor.fetchone()
    seller_dict = {}
    seller_dict["id"] = row.seller_id
    seller_dict["seller_name"] = row.seller_name
    seller_dict["email"] = row.email
    return seller_dict
