from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
from data_service import get_active_rental_contracts, get_active_rental_items

tab5_bp = Blueprint("tab5_bp", __name__, url_prefix="/tab5")

@tab5_bp.route("/")
def show_tab5():
    print("Loading /tab5/ endpoint")
    with DatabaseConnection() as conn:
        contracts = get_active_rental_contracts(conn)
        # Fetch all items, not just active rental ones
        all_items = conn.execute("SELECT * FROM id_item_master").fetchall()
        active_items = get_active_rental_items(conn)

    all_items = [dict(row) for row in all_items]  # Full item set
    laundry_items = [
        item for item in [dict(row) for row in active_items]
        if item.get("last_contract_num", "").lower().startswith("l")
    ]

    filter_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_common_name = request.args.get("common_name", "").lower().strip()

    filtered_items = laundry_items
    if filter_contract:
        filtered_items = [item for item in filtered_items if filter_contract in item["last_contract_num"].lower()]
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in item.get("common_name", "").lower()]

    contract_map = defaultdict(list)
    for item in filtered_items:
        contract = item.get("last_contract_num", "Unknown")
        contract_map[contract].append(item)

    parent_data = []
    child_map = {}
    for contract, item_list in contract_map.items():
        common_name_map = defaultdict(list)
        for item in item_list:
            common_name = item.get("common_name", "Unknown")
            common_name_map[common_name].append(item)

        child_data = {}
        for common_name, items in common_name_map.items():
            # Total Available across all contracts
            total_available = sum(1 for item in all_items if item["common_name"] == common_name and item["status"] == "Ready to Rent")
            # On Rent/Delivered for non-L contracts only
            on_rent = sum(1 for item in all_items if item["common_name"] == common_name and 
                          item["status"] in ["On Rent", "Delivered"] and 
                          not item.get("last_contract_num", "").lower().startswith("l"))
            service = len(items) - sum(1 for item in items if item["status"] == "Ready to Rent") - sum(1 for item in items if item["status"] in ["On Rent", "Delivered"])
            child_data[common_name] = {
                "total": len(items),  # Total on this L contract
                "available": total_available,  # All Ready to Rent
                "on_rent": on_rent,  # Non-L On Rent/Delivered
                "service": service
            }

        parent_data.append({
            "contract": contract,
            "total": len(item_list)
        })
        child_map[contract] = child_data

    parent_data.sort(key=lambda x: x["contract"].lower())

    return render_template(
        "tab5.html",
        parent_data=parent_data,
        child_map=child_map,
        filter_contract=filter_contract,
        filter_common_name=filter_common_name
    )

@tab5_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    print("Hit /tab5/subcat_data endpoint")
    contract = request.args.get('contract')
    common_name = request.args.get('common_name')
    page = int(request.args.get('page', 1))
    per_page = 20

    with DatabaseConnection() as conn:
        items = get_active_rental_items(conn)

    laundry_items = [
        item for item in [dict(row) for row in items]
        if item.get("last_contract_num", "").lower().startswith("l")
    ]

    filter_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_common_name = request.args.get("common_name_filter", "").lower().strip()

    filtered_items = laundry_items
    if filter_contract:
        filtered_items = [item for item in filtered_items if filter_contract in item["last_contract_num"].lower()]
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in item.get("common_name", "").lower()]

    subcat_items = [
        item for item in filtered_items
        if item.get("last_contract_num") == contract and item.get("common_name") == common_name
    ]

    total_items = len(subcat_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = subcat_items[start:end]

    print(f"AJAX: Contract: {contract}, Common Name: {common_name}, Total Items: {total_items}, Page: {page}")

    return jsonify({
        "items": [{
            "tag_id": item["tag_id"],
            "common_name": item["common_name"],
            "status": item["status"],
            "bin_location": item["bin_location"],
            "quality": item["quality"],
            "last_contract_num": item["last_contract_num"],
            "date_last_scanned": item.get("date_last_scanned", "N/A"),
            "last_scanned_by": item.get("last_scanned_by", "Unknown")
        } for item in paginated_items],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    })