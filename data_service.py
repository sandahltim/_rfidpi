def get_active_rental_contracts(conn):
    """
    Returns a list of active rental contracts using a subquery to fetch the latest client_name.
    """
    query = """
       SELECT DISTINCT im.last_contract_num,
           (SELECT it2.client_name 
            FROM id_transactions it2 
            WHERE it2.contract_number = im.last_contract_num 
            ORDER BY it2.scan_date DESC 
            LIMIT 1) AS client_name
       FROM id_item_master im
       WHERE im.status IN ('On Rent', 'Delivered')
       ORDER BY im.last_contract_num
    """
    return conn.execute(query).fetchall()


def get_active_rental_items(conn):
    """
    Returns all active rental items from the inventory.
    """
    query_items = """
       SELECT * FROM id_item_master
       WHERE status IN ('On Rent', 'Delivered')
       ORDER BY last_contract_num, tag_id
    """
    return conn.execute(query_items).fetchall()

