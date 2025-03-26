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
            conn = sqlite3.connect(HAND_COUNTED_DB, timeout=10)
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
        os.chmod(HAND_COUNTED_DB, 0o666)
    except Exception:
        pass  # Silently ignore any errors to remove debug/log output

@tab5_bp.route("/")
def show_tab5():
    init_hand_counted_db()
    try:
        with DatabaseConnection() as conn:
            contracts = get_active_rental_contracts(conn)
            all_items = conn.execute("SELECT * FROM id_item_master").fetchall()
            active_items = get_active_rental_items(conn)

        with sqlite3.connect(HAND_COUNTED_DB, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            hand_counted_items = conn.execute(
                "SELECT * FROM hand_counted_items WHERE last_contract_num LIKE 'L%'"
            ).fetchall()

        all_items = [dict(row) for row in all_items]
        laundry_items = [
            item for item in [dict(row) for row in active_items]
            if item.get("last_contract_num", "").lower().startswith("l")
        ]
        hand_counted = [dict(row) for row in hand_counted_items] if hand_counted_items else []

        filter_contract = request.args.get("last_contract_num", "").lower().strip()
        filter_common_name = request.args.get("common_name", "").lower().strip()

        filtered_items = laundry_items
        if filter_contract:
            filtered_items = [
                itm for itm in filtered_items 
                if filter_contract in itm["last_contract_num"].lower()
            ]
        if filter_common_name:
            filtered_items = [
                itm for itm in filtered_items 
                if filter_common_name in itm.get("common_name", "").lower()
            ]

        contract_map = defaultdict(list)
        for itm in filtered_items:
            contract = itm.get("last_contract_num", "Unknown")
            contract_map[contract].append(itm)
        for itm in hand_counted:
            contract = itm.get("last_contract_num", "Unknown")
            contract_map[contract].append(itm)

        parent_data = []
        child_map = {}
        grandchild_map = defaultdict(lambda: defaultdict(list))
        for contract, item_list in contract_map.items():
            common_name_map = defaultdict(list)
            for itm in item_list:
                cname = itm.get("common_name", "Unknown")
                common_name_map[cname].append(itm)
                grandchild_map[contract][cname].append({
                    "tag_id": itm.get("tag_id", "N/A"),
                    "common_name": cname,
                    "status": itm.get("status", "Hand Counted" if itm.get("tag_id") is None else "N/A"),
                    "bin_location": itm.get("bin_location", "N/A"),
                    "quality": itm.get("quality", "N/A"),
                    "last_contract_num": contract,
                    "date_last_scanned": itm.get("date_last_scanned", "N/A"),
                    "last_scanned_by": itm.get("last_scanned_by", "Unknown")
                })

            child_data = {}
            for cname, items in common_name_map.items():
                rfid_items = [i for i in items if i.get("tag_id") is not None]
                hand_items = [i for i in items if i.get("tag_id") is None]
                total_rfid = len(rfid_items)
                total_hand = sum(i.get("total_items", 0) for i in hand_items)
                total_items = total_rfid + total_hand
                total_available = sum(
                    1 for i in all_items 
                    if i["common_name"] == cname and i["status"] == "Ready to Rent"
                )
                on_rent = sum(
                    1 for i in all_items 
                    if i["common_name"] == cname 
                    and i["status"] in ["On Rent", "Delivered"] 
                    and i.get("last_contract_num", "") 
                    and not i["last_contract_num"].lower().startswith("l")
                )
                service = (
                    total_rfid 
                    - sum(1 for i in rfid_items if i.get("status") == "Ready to Rent")
                    - sum(1 for i in rfid_items if i.get("status", "") in ["On Rent", "Delivered"])
                    if rfid_items else 0
                )
                child_data[cname] = {
                    "total": total_items,
                    "available": total_available,
                    "on_rent": on_rent,
                    "service": service
                }

            rfid_total = len([i for i in item_list if i.get("tag_id") is not None])
            hand_total = sum(i.get("total_items", 0) for i in item_list if i.get("tag_id") is None)
            parent_data.append({
                "contract": contract,
                "total": rfid_total + hand_total
            })
            child_map[contract] = child_data

        parent_data.sort(key=lambda x: x["contract"].lower())

        return render_template(
            "tab5.html",
            parent_data=parent_data,
            child_map=child_map,
            grandchild_map=grandchild_map,
            child_map_json=child_map,
            filter_contract=filter_contract,
            filter_common_name=filter_common_name
        )
    except Exception:
        return "Internal Server Error", 500

@tab5_bp.route("/save_hand_counted", methods=["POST"])
def save_hand_counted():
    try:
        common_name = request.form.get("common_name")
        last_contract_num = request.form.get("last_contract_num")
        total_items = int(request.form.get("total_items", 0))
        last_scanned_by = request.form.get("last_scanned_by")
        date_last_scanned = request.form.get("date_last_scanned")

        with sqlite3.connect(HAND_COUNTED_DB, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hand_counted_items (
                    last_contract_num, common_name, total_items, tag_id, date_last_scanned, last_scanned_by
                )
                VALUES (?, ?, ?, NULL, ?, ?)
            """, (last_contract_num, common_name, total_items, date_last_scanned, last_scanned_by))
            conn.commit()

        return redirect(url_for("tab5_bp.show_tab5"))
    except Exception:
        return "Internal Server Error", 500

@tab5_bp.route("/update_hand_counted", methods=["POST"])
def update_hand_counted():
    try:
        common_name = request.form.get("common_name")
        last_contract_num = request.form.get("last_contract_num")
        returned_qty = int(request.form.get("total_items", 0))
        last_scanned_by = request.form.get("last_scanned_by")
        date_last_scanned = request.form.get("date_last_scanned")

        if not last_contract_num.startswith("L"):
            return "Contract must start with 'L'", 400

        with sqlite3.connect(HAND_COUNTED_DB, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, total_items FROM hand_counted_items 
                WHERE last_contract_num = ? AND common_name = ?
                """,
                (last_contract_num, common_name)
            )
            row = cursor.fetchone()

            if not row:
                return "No matching L contract found", 404

            orig_id, orig_total = row["id"], row["total_items"]
            new_total = orig_total - returned_qty

            if new_total < 0:
                return "Returned quantity exceeds original total", 400

            if new_total == 0:
                cursor.execute("DELETE FROM hand_counted_items WHERE id = ?", (orig_id,))
            else:
                cursor.execute(
                    """
                    UPDATE hand_counted_items SET total_items = ? 
                    WHERE id = ?
                    """,
                    (new_total, orig_id)
                )

            closed_contract = "C" + last_contract_num[1:]
            cursor.execute("""
                INSERT INTO hand_counted_items (
                    last_contract_num, common_name, total_items, tag_id, date_last_scanned, last_scanned_by
                )
                VALUES (?, ?, ?, NULL, ?, ?)
            """, (closed_contract, common_name, returned_qty, date_last_scanned, last_scanned_by))

            conn.commit()

        return redirect(url_for("tab5_bp.show_tab5"))
    except Exception:
        return "Internal Server Error", 500

@tab5_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    contract = request.args.get('contract')
    common_name = request.args.get('common_name')
    page = int(request.args.get('page', 1))
    per_page = 20

    with DatabaseConnection() as conn:
        items = get_active_rental_items(conn)

    with sqlite3.connect(HAND_COUNTED_DB, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        hand_items = conn.execute(
            "SELECT * FROM hand_counted_items WHERE last_contract_num = ? AND common_name = ?",
            (contract, common_name)
        ).fetchall()

    laundry_items = [
        itm for itm in [dict(row) for row in items]
        if itm.get("last_contract_num", "") == contract 
        and itm.get("common_name", "") == common_name
    ]
    hand_counted = [dict(row) for row in hand_items]

    filter_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_common_name = request.args.get("common_name_filter", "").lower().strip()

    filtered_items = laundry_items + hand_counted
    if filter_contract:
        filtered_items = [
            i for i in filtered_items 
            if filter_contract in i["last_contract_num"].lower()
        ]
    if filter_common_name:
        filtered_items = [
            i for i in filtered_items 
            if filter_common_name in i.get("common_name", "").lower()
        ]

    total_items = len(filtered_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = filtered_items[start:end]

    response = {
        "items": [{
            "tag_id": itm.get("tag_id", "N/A"),
            "common_name": itm["common_name"],
            "status": itm.get("status", "Hand Counted"),
            "bin_location": itm.get("bin_location", "N/A"),
            "quality": itm.get("quality", "N/A"),
            "last_contract_num": itm["last_contract_num"],
            "date_last_scanned": itm.get("date_last_scanned", "N/A"),
            "last_scanned_by": itm.get("last_scanned_by", "Unknown")
        } for itm in paginated_items],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    }
    return jsonify(response)
