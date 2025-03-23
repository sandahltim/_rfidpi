from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
from data_service import get_active_rental_contracts, get_active_rental_items
import logging
import os

# Ensure log directory exists
LOG_DIR = "/home/tim/test_rfidpi/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/rfid_dash_test.log"),
        logging.StreamHandler()
    ],
    force=True
)

tab1_bp = Blueprint("tab1_bp", __name__, url_prefix="/tab1")

@tab1_bp.route("/")
def show_tab1():
    logging.debug("Loading /tab1/ endpoint")
    try:
        with DatabaseConnection() as conn:
            contracts = get_active_rental_contracts(conn)
            items = get_active_rental_items(conn)
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
                "contract_num": contract,
                "client_name": row["client_name"] or "UNKNOWN",
                "total_items": total_items,
                "scan_date": trans_info["scan_date"],
                "transaction_notes": trans_info["notes"]
            })

        # Apply filters
        filter_contract_num = request.args.get("contract_num", "").lower().strip()
        filter_client_name = request.args.get("client_name", "").lower().strip()

        filtered_parent_data = parent_data
        if filter_contract_num:
            filtered_parent_data = [item for item in filtered_parent_data if filter_contract_num in item["contract_num"].lower()]
        if filter_client_name:
            filtered_parent_data = [item for item in filtered_parent_data if filter_client_name in item["client_name"].lower()]

        middle_data = {}
        for contract, common_names in contract_map.items():
            middle_data[contract] = [
                {"common_name": name, "total_on_contract": len(items)}
                for name, items in common_names.items()
            ]

        per_page = 20
        total_items = len(filtered_parent_data)
        total_pages = (total_items + per_page - 1) // per_page
        page = request.args.get("page", 1, type=int)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page
        paginated_data = filtered_parent_data[start:end]

        logging.debug(f"Rendering tab1 with parent_data: {paginated_data}")
        return render_template(
            "tab1.html",
            parent_data=paginated_data,
            middle_data=middle_data,
            contract_map=contract_map,
            current_page=page,
            total_pages=total_pages,
            filter_contract_num=filter_contract_num,
            filter_client_name=filter_client_name
        )
    except Exception as e:
        import traceback
        logging.error(f"Error in show_tab1: {e}\n{traceback.format_exc()}")
        return "Internal Server Error", 500

@tab1_bp.route("/refresh_data", methods=["GET"])
def refresh_data():
    logging.debug("Hit /tab1/refresh_data endpoint")
    try:
        with DatabaseConnection() as conn:
            contracts = get_active_rental_contracts(conn)
            items = get_active_rental_items(conn)
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
        middle_map = {}
        for row in contracts:
            contract = row["last_contract_num"]
            total_items = sum(len(items) for items in contract_map[contract].values())
            trans_info = trans_map.get(contract, {"scan_date": "N/A", "notes": "N/A"})
            parent_data.append({
                "contract_num": contract,
                "client_name": row["client_name"] or "UNKNOWN",
                "total_items": total_items,
                "scan_date": trans_info["scan_date"],
                "transaction_notes": trans_info["notes"]
            })
            middle_map[contract] = [
                {"common_name": name, "total_on_contract": len(items)}
                for name, items in contract_map[contract].items()
            ]

        # Apply filters from request (for consistency with show_tab1)
        filter_contract_num = request.args.get("contract_num", "").lower().strip()
        filter_client_name = request.args.get("client_name", "").lower().strip()

        filtered_parent_data = parent_data
        if filter_contract_num:
            filtered_parent_data = [item for item in filtered_parent_data if filter_contract_num in item["contract_num"].lower()]
        if filter_client_name:
            filtered_parent_data = [item for item in filtered_parent_data if filter_client_name in item["client_name"].lower()]

        logging.debug(f"Tab1 refresh data: parent_data={filtered_parent_data}, middle_map={middle_map}")
        return jsonify({
            "parent_data": filtered_parent_data,
            "middle_map": middle_map
        })
    except Exception as e:
        import traceback
        logging.error(f"Error in tab1 refresh_data: {e}\n{traceback.format_exc()}")
        return "Internal Server Error", 500