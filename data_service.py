def get_active_rental_contracts(conn, filter_contract="", filter_common="", sort="last_contract_num:asc", since_date=None):
    """
    Returns a list of active rental contracts using a subquery to fetch the latest client_name.
    """
    sort_field, sort_order = sort.split(":") if ":" in sort else ("last_contract_num", "asc")
    query = """
       SELECT DISTINCT last_contract_num,
           (SELECT it2.client_name 
            FROM id_transactions it2 
            WHERE it2.contract_number = id_item_master.last_contract_num 
            ORDER BY it2.scan_date DESC 
            LIMIT 1) AS client_name
       FROM id_item_master
       WHERE status IN ('On Rent', 'Delivered')
    """
    params = []
    if filter_contract:
        query += " AND last_contract_num LIKE ?"
        params.append(f"%{filter_contract}%")
    if filter_common:
        query += " AND common_name LIKE ?"
        params.append(f"%{filter_common}%")
    if since_date:
        query += " AND date_last_scanned >= ?"
        params.append(since_date)
    query += f" ORDER BY {sort_field} {sort_order.upper()}"
    return conn.execute(query, params).fetchall()


def get_active_rental_items(conn, filter_contract="", filter_common="", sort="last_contract_num:asc", since_date=None):
    """
    Returns all active rental items from the inventory.
    """
    sort_field, sort_order = sort.split(":") if ":" in sort else ("last_contract_num", "asc")
    query_items = """
       SELECT * FROM id_item_master
       WHERE status IN ('On Rent', 'Delivered')
    """
    params = []
    if filter_contract:
        query_items += " AND last_contract_num LIKE ?"
        params.append(f"%{filter_contract}%")
    if filter_common:
        query_items += " AND common_name LIKE ?"
        params.append(f"%{filter_common}%")
    if since_date:
        query_items += " AND date_last_scanned >= ?"
        params.append(since_date)
    query_items += f" ORDER BY {sort_field} {sort_order.upper()}"
    return conn.execute(query_items, params).fetchall()