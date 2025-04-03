from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection

tab1_bp = Blueprint("tab1_bp", __name__, url_prefix="/tab1")

@tab1_bp.route("/")
def show_tab1():
    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master WHERE status IN ('Delivered', 'On Rent')").fetchall()
    items = [dict(row) for row in rows]

    contract_totals = defaultdict(lambda: {"total": 0, "client_name": None, "first_scan_date": None, "items": []})
    for item in items:
        contract = item.get("last_contract_num")
        if not contract:
            continue
        contract_totals[contract]["total"] += 1
        contract_totals[contract]["items"].append(item)
        if not contract_totals[contract]["client_name"]:
            contract_totals[contract]["client_name"] = item.get("client_name")
        current_first_scan = contract_totals[contract]["first_scan_date"]
        item_scan_date = item.get("date_last_scanned")
        if item_scan_date and (not current_first_scan or item_scan_date < current_first_scan):
            contract_totals[contract]["first_scan_date"] = item_scan_date

    parent_data = [
        {
            "contract": contract,
            "total": info["total"],
            "client_name": info["client_name"],
            "first_scan_date": info["first_scan_date"]
        }
        for contract, info in contract_totals.items()
    ]
    parent_data.sort(key=lambda x: x["contract"])

    child_map = {}
    for contract, info in contract_totals.items():
        rental_class_totals = defaultdict(lambda: {"total": 0, "available": 0, "on_rent": 0, "service": 0})
        for item in info["items"]:
            rental_class_id = item.get("rental_class_num", "unknown")
            common_name = item.get("common_name", "Unknown")
            rental_class_totals[rental_class_id]["common_name"] = common_name
            rental_class_totals[rental_class_id]["total"] += 1
            if item["status"] == "Ready to Rent":
                rental_class_totals[rental_class_id]["available"] += 1
            elif item["status"] in ["On Rent", "Delivered"]:
                rental_class_totals[rental_class_id]["on_rent"] += 1
            else:
                rental_class_totals[rental_class_id]["service"] += 1
        child_map[contract] = dict(rental_class_totals)

    return render_template("tab1.html", parent_data=parent_data, child_map=child_map)

@tab1_bp.route("/data", methods=["GET"])
def tab1_data():
    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master WHERE status IN ('Delivered', 'On Rent')").fetchall()
    items = [dict(row) for row in rows]

    contract_totals = defaultdict(lambda: {"total": 0, "client_name": None, "first_scan_date": None, "items": []})
    for item in items:
        contract = item.get("last_contract_num")
        if not contract:
            continue
        contract_totals[contract]["total"] += 1
        contract_totals[contract]["items"].append(item)
        if not contract_totals[contract]["client_name"]:
            contract_totals[contract]["client_name"] = item.get("client_name")
        current_first_scan = contract_totals[contract]["first_scan_date"]
        item_scan_date = item.get("date_last_scanned")
        if item_scan_date and (not current_first_scan or item_scan_date < current_first_scan):
            contract_totals[contract]["first_scan_date"] = item_scan_date

    parent_data = [
        {
            "contract": contract,
            "total": info["total"],
            "client_name": info["client_name"],
            "first_scan_date": info["first_scan_date"]
        }
        for contract, info in contract_totals.items()
    ]
    parent_data.sort(key=lambda x: x["contract"])

    child_map = {}
    for contract, info in contract_totals.items():
        rental_class_totals = defaultdict(lambda: {"total": 0, "available": 0, "on_rent": 0, "service": 0})
        for item in info["items"]:
            rental_class_id = item.get("rental_class_num", "unknown")
            common_name = item.get("common_name", "Unknown")
            rental_class_totals[rental_class_id]["common_name"] = common_name
            rental_class_totals[rental_class_id]["total"] += 1
            if item["status"] == "Ready to Rent":
                rental_class_totals[rental_class_id]["available"] += 1
            elif item["status"] in ["On Rent", "Delivered"]:
                rental_class_totals[rental_class_id]["on_rent"] += 1
            else:
                rental_class_totals[rental_class_id]["service"] += 1
        child_map[contract] = dict(rental_class_totals)

    return jsonify({
        "parent_data": parent_data,
        "child_map": child_map
    })

@tab1_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    contract = request.args.get('contract')
    common_name = request.args.get('common_name')
    page = int(request.args.get('page', 1))
    per_page = 20

    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master WHERE last_contract_num = ? AND status IN ('Delivered', 'On Rent')", (contract,)).fetchall()
    items = [dict(row) for row in rows]

    filtered_items = [item for item in items if item.get("common_name") == common_name]
    total_items = len(filtered_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = filtered_items[start:end]

    return jsonify({
        "items": paginated_items,
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    })