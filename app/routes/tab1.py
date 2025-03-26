from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
from data_service import get_active_rental_contracts, get_active_rental_items

tab1_bp = Blueprint("tab1_bp", __name__, url_prefix="/tab1")

def get_tab1_data(page=1, per_page=20):
    try:
        with DatabaseConnection() as conn:
            contracts = get_active_rental_contracts(conn)
            items = get_active_rental_items(conn)
            trans = conn.execute("""
                SELECT contract_number, MAX(scan_date) as scan_date, notes
                FROM id_transactions
                WHERE contract_number IN (
                    SELECT last_contract_num 
                    FROM id_item_master 
                    WHERE status IN ('On Rent', 'Delivered')
                )
                GROUP BY contract_number, notes
            """).fetchall()

        trans_map = {
            row["contract_number"]: {
                "scan_date": row["scan_date"],
                "notes": row["notes"]
            } 
            for row in trans
        }
        contract_map = defaultdict(lambda: defaultdict(list))
        for item in [dict(row) for row in items]:
            contract_map[item["last_contract_num"]][item["common_name"]].append(item)

        parent_data = []
        for row in contracts:
            contract = row["last_contract_num"]
            total_items = sum(len(i) for i in contract_map[contract].values())
            trans_info = trans_map.get(contract, {"scan_date": "N/A", "notes": "N/A"})
            parent_data.append({
                "contract_num": contract,
                "client_name": row["client_name"] or "UNKNOWN",
                "total_items": total_items,
                "scan_date": trans_info["scan_date"],
                "transaction_notes": trans_info["notes"]
            })

        middle_data = {}
        for contract, common_names in contract_map.items():
            middle_data[contract] = [
                {"common_name": name, "total_on_contract": len(items)}
                for name, items in common_names.items()
            ]

        total_items = len(parent_data)
        total_pages = (total_items + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page
        paginated_data = parent_data[start:end]

        return {
            "parent_data": paginated_data,
            "middle_data": middle_data,
            "contract_map": contract_map,
            "current_page": page,
            "total_pages": total_pages
        }
    except Exception as e:
        # Preserve the raise to handle the exception at a higher level
        raise

@tab1_bp.route("/", methods=["GET"])
def show_tab1():
    page = request.args.get("page", 1, type=int)
    data = get_tab1_data(page)
    return render_template(
        "tab1.html",
        parent_data=data["parent_data"],
        middle_data=data["middle_data"],
        contract_map=data["contract_map"],
        current_page=data["current_page"],
        total_pages=data["total_pages"]
    )

@tab1_bp.route("/refresh_data", methods=["GET"])
def refresh_tab1_data():
    try:
        page = request.args.get("page", 1, type=int)
        data = get_tab1_data(page)
        return jsonify({
            "parent_data": [dict(row) for row in data["parent_data"]],
            "middle_map": data["middle_data"],
            "contract_map": {
                k: {
                    sk: [dict(r) for r in sv] 
                    for sk, sv in v.items()
                } 
                for k, v in data["contract_map"].items()
            },
            "current_page": data["current_page"],
            "total_pages": data["total_pages"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
