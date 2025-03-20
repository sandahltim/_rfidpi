from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from collections import defaultdict
from db_connection import DatabaseConnection
from data_service import get_active_rental_contracts, get_active_rental_items
import sqlite3
import os

tab5_bp = Blueprint("tab5_bp", __name__, url_prefix="/tab5")

HAND_COUNTED_DB = "/home/tim/test_rfidpi/tab5_hand_counted.db"

def init_hand_counted_db():
    try:
        if not os.path.exists(HAND_COUNTED_DB):
            conn = sqlite3.connect(HAND_COUNTED_DB)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hand_counted_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_contract_num TEXT,
                    common_name TEXT,
                    total_items INTEGER,
                    tag_id TEXT DEFAULT NULL,
                    date_last_scanned TEXT,
                    last_scanned_by TEXT
                )
            """)
            conn.commit()
            conn.close()
            print("Initialized tab5_hand_counted.db")
        os.chmod(HAND_COUNTED_DB, 0o666)
    except Exception as e:
        print(f"Error initializing tab5_hand_counted.db: {e}")

@tab5_bp.route("/")
def show_tab5():
    print("Loading /tab5/ endpoint")
    init_hand_counted_db()

    try:
        with DatabaseConnection() as conn:
            contracts = get_active_rental_contracts(conn)
            all_items = conn.execute("SELECT * FROM id_item_master").fetchall()
            active_items = get_active_rental_items(conn)

        with sqlite3.connect(HAND_COUNTED_DB) as conn:
            hand_counted_items = conn.execute("SELECT * FROM hand_counted_items").fetchall()

        all_items = [dict(row) for row in all_items]
        laundry_items = [
            item for item in [dict(row) for row in active_items]
            if item.get("last_contract_num", "").lower().startswith("l")
        ]
        hand_counted = [dict(row) for row in hand_counted_items]

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
        for item in hand_counted:
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
                rfid_items = [i for i in items if i.get("tag_id") is not None]
                hand_items = [i for i in items if i.get("tag_id") is None]
                total_rfid = len(rfid_items)
                total_hand = sum(i["total_items"] for i in hand_items) if hand_items else 0
                total_items = total_rfid + total_hand
                total_available = sum(1 for item in all_items if item["common_name"] == common_name and item["status"] == "Ready to Rent")
                on_rent = sum(1 for item in all_items if item["common_name"] == common_name and 
                              item["status"] in ["On Rent", "Delivered"] and 
                              (item.get("last_contract_num", "") and not item["last_contract_num"].lower().startswith("l")))
                # Service only for RFID items, hand-counted don't have status
                service = total_rfid - sum(1 for item in rfid_items if item.get("status") == "Ready to Rent") - sum(1 for item in rfid_items if item.get("status", "") in ["On Rent", "Delivered"]) if rfid_items else 0
                child_data[common_name] = {
                    "total": total_items,
                    "available": total_available,
                    "on_rent": on_rent,
                    "service": service
                }

            total_contract = sum(
                len([i for i in item_list if i.get("tag_id") is not None]) + 
                sum(i["total_items"] for i in item_list if i.get("tag_id") is None)
            )
            parent_data.append({
                "contract": contract,
                "total": total_contract
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
    except Exception as e:
        print(f"Error in show_tab5: {e}")
        return "Internal Server Error", 500

@tab5_bp.route("/save_hand_counted", methods=["POST"])
def save_hand_counted():
    print("Saving hand-counted entry")
    try:
        common_name = request.form.get("common_name")
        last_contract_num = request.form.get("last_contract_num")
        total_items = int(request.form.get("total_items", 0))
        last_scanned_by = request.form.get("last_scanned_by")
        date_last_scanned = request.form.get("date_last_scanned")

        with sqlite3.connect(HAND_COUNTED_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hand_counted_items (last_contract_num, common_name, total_items, tag_id, date_last_scanned, last_scanned_by)
                VALUES (?, ?, ?, NULL, ?, ?)
            """, (last_contract_num, common_name, total_items, date_last_scanned, last_scanned_by))
            conn.commit()

        return redirect(url_for("tab5_bp.show_tab5"))
    except Exception as e:
        print(f"Error saving hand-counted entry: {e}")
        return "Internal Server Error", 500

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