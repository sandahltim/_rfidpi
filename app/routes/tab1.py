from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
from data_service import get_active_rental_contracts, get_active_rental_items

tab1_bp = Blueprint("tab1", __name__, url_prefix="/tab1")

@tab1_bp.route("/")
def show_tab1():
    filter_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_common = request.args.get("common_name", "").lower().strip()
    sort = request.args.get("sort", "last_contract_num:asc")

    with DatabaseConnection() as conn:
        contracts = get_active_rental_contracts(conn, filter_contract, filter_common, sort)
        items = get_active_rental_items(conn, filter_contract, filter_common, sort)
        trans = conn.execute("""
            SELECT contract_number, MAX(scan_date) as scan_date, notes
            FROM id_transactions
            WHERE contract_number IN (SELECT last_contract_num FROM id_item_master WHERE status IN ('On Rent', 'Delivered'))
            GROUP BY contract_number, notes
        """).fetchall()

    trans_map = {row["contract_number"]: {"scan_date": row["scan_date"], "notes": row["notes"]} for row in trans}
    contract_map = defaultdict(lambda: defaultdict(list))
    for item in [dict(row) for row in items]:
        contract_map[item["last_contract_num"]][item["common_name"]].append(item)

    parent_data = []
    for row in contracts:
        contract = row["last_contract_num"]
        total_items = sum(len(items) for items in contract_map[contract].values())
        trans_info = trans_map.get(contract, {"scan_date": "N/A", "notes": "N/A"})
        parent_data.append({
            "contract": contract,
            "client_name": row["client_name"] or "UNKNOWN",
            "total": total_items,
            "scan_date": trans_info["scan_date"],
            "transaction_notes": trans_info["notes"]
        })

    child_map = {}
    for contract, common_names in contract_map.items():
        child_map[contract] = {}
        for common_name, items in common_names.items():
            total_items = len(items)
            total_available = sum(1 for item in items if item["status"] == "Ready to Rent")
            on_rent = total_items
            service = sum(1 for item in items if item["status"] not in ["Ready to Rent", "On Rent", "Delivered"])
            child_map[contract][common_name] = {
                "total": total_items,
                "available": total_available,
                "on_rent": on_rent,
                "service": service
            }

    per_page = 20
    total_items = len(parent_data)
    total_pages = (total_items + per_page - 1) // per_page
    page = request.args.get("page", 1, type=int)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_data = parent_data[start:end]

    return render_template(
        "tab1.html",
        parent_data=paginated_data,
        child_map=child_map,
        contract_map=contract_map,
        filter_contract=filter_contract,
        filter_common=filter_common,
        sort=sort,
        current_page=page,
        total_pages=total_pages
    )

@tab1_bp.route("/data", methods=["GET"])
def tab1_data():
    contract = request.args.get('contract')
    common_name = request.args.get('common_name')
    page = int(request.args.get('page', 1))
    per_page = 20
    filter_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_common = request.args.get("common_name_filter", "").lower().strip()
    sort = request.args.get("sort", "last_contract_num:asc")  # Fixed sort param

    with DatabaseConnection() as conn:
        items = get_active_rental_items(conn, filter_contract, filter_common, sort)

    filtered_items = [
        dict(item) for item in items
        if (not contract or item["last_contract_num"] == contract) and
           (not common_name or item["common_name"] == common_name)
    ]

    total_items = len(filtered_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = filtered_items[start:end]

    return jsonify({
        "items": [{
            "tag_id": item.get("tag_id", "N/A"),
            "common_name": item["common_name"],
            "status": item.get("status", "N/A"),
            "bin_location": item.get("bin_location", "N/A"),
            "quality": item.get("quality", "N/A"),
            "last_contract_num": item["last_contract_num"],
            "date_last_scanned": item.get("date_last_scanned", "N/A"),
            "last_scanned_by": item.get("last_scanned_by", "Unknown"),
            "notes": item.get("notes", "N/A")
        } for item in paginated_items],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    })