def get_active_rental_contracts(conn, filter_contract="", filter_common="", sort="last_contract_num:asc", since_date=None):
    """
    Returns a list of active rental contracts with latest client_name.
    """
    sort_field, sort_order = sort.split(":") if ":" in sort else ("last_contract_num", "asc")
    query = """
       SELECT DISTINCT im.last_contract_num,
           (SELECT it2.client_name 
            FROM id_transactions it2 
            WHERE it2.contract_number = im.last_contract_num 
            ORDER BY it2.scan_date DESC 
            LIMIT 1) AS client_name,
           MAX(im.date_last_scanned) AS scan_date,
           MAX(it.transaction_notes) AS transaction_notes
       FROM id_item_master im
       LEFT JOIN id_transactions it ON im.last_contract_num = it.contract_number
       WHERE im.status IN ('On Rent', 'Delivered')
    """
    params = []
    if filter_contract:
        query += " AND im.last_contract_num LIKE ?"
        params.append(f"%{filter_contract}%")
    if filter_common:
        query += " AND im.common_name LIKE ?"
        params.append(f"%{filter_common}%")
    if since_date:
        query += " AND im.date_last_scanned >= ?"
        params.append(since_date)
    query += f" GROUP BY im.last_contract_num ORDER BY {sort_field} {sort_order.upper()}"
    return conn.execute(query, params).fetchall()

def get_active_rental_items(conn, filter_contract="", filter_common="", sort="last_contract_num:asc", since_date=None):
    """
    Returns all active rental items with rental_class_id from seed_rental_classes.
    """
    sort_field, sort_order = sort.split(":") if ":" in sort else ("last_contract_num", "asc")
    query_items = """
       SELECT im.tag_id, im.common_name, src.rental_class_id, im.status, im.bin_location, 
              im.quality, im.last_contract_num, im.date_last_scanned, im.last_scanned_by, im.notes
       FROM id_item_master im
       LEFT JOIN seed_rental_classes src ON im.common_name = src.common_name
       WHERE im.status IN ('On Rent', 'Delivered')
    """
    params = []
    if filter_contract:
        query_items += " AND im.last_contract_num LIKE ?"
        params.append(f"%{filter_contract}%")
    if filter_common:
        query_items += " AND im.common_name LIKE ?"
        params.append(f"%{filter_common}%")
    if since_date:
        query_items += " AND im.date_last_scanned >= ?"
        params.append(since_date)
    query_items += f" ORDER BY {sort_field} {sort_order.upper()}"
    return conn.execute(query_items, params).fetchall()