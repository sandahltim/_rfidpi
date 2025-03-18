from flask import Blueprint, render_template, request
from collections import defaultdict
from db_connection import DatabaseConnection
from data_service import get_active_rental_contracts, get_active_rental_items

tab1_bp = Blueprint("tab1", __name__, url_prefix="/tab1")

@tab1_bp.route("/")
def show_tab1():
    with DatabaseConnection() as conn:
        contracts = get_active_rental_contracts(conn)
        items = get_active_rental_items(conn)
        # Fetch latest scan_date and notes from id_transactions
        trans = conn.execute("""
            SELECT contract_number, MAX(scan_date) as scan_date, notes
            FROM id_transactions
            WHERE contract_number IN (SELECT last_contract_num FROM id_item_master WHERE status IN ('On Rent', 'Delivered'))
            GROUP BY contract_number, notes
        """).fetchall()

    # Map transactions to contracts
    trans_map = {row["contract_number"]: {"scan_date": row["scan_date"], "notes": row["notes"]} for row in trans}

    # Group items by contract and common_name
    contract_map = defaultdict(lambda: defaultdict(list))
    for item in [dict(row) for row in items]:
        contract_map[item["last_contract_num"]][item["common_name"]].append(item)

    # Parent data with total_items, scan_date, and transaction_notes
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

    # Middle child: Aggregate by common_name
    middle_data = {}
    for contract, common_names in contract_map.items():
        middle_data[contract] = [
            {"common_name": name, "total_on_contract": len(items)}
            for name, items in common_names.items()
        ]

    # Pagination for parent
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
        middle_data=middle_data,
        contract_map=contract_map,
        current_page=page,
        total_pages=total_pages
    )
