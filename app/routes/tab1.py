from flask import Blueprint, render_template, request
from collections import defaultdict
from db_connection import DatabaseConnection
from data_service import get_active_rental_contracts, get_active_rental_items

tab1_bp = Blueprint("tab1", __name__, url_prefix="/tab1")

@tab1_bp.route("/")
def show_tab1():
    # Use the centralized database connection
    with DatabaseConnection() as conn:
        contracts = get_active_rental_contracts(conn)
        items = get_active_rental_items(conn)
    
    # Group items by contract number
    contract_map = defaultdict(list)
    for item in [dict(row) for row in items]:
        contract_map[item["last_contract_num"]].append(item)
    
    # Prepare parent data for rental contracts
    parent_data = [
        {"contract_num": row["last_contract_num"], "client_name": row["client_name"] or "UNKNOWN"}
        for row in contracts
    ]
    
    # Pagination
    per_page = 40
    total_items = len(parent_data)
    total_pages = (total_items + per_page - 1) // per_page
    page = request.args.get("page", 1, type=int)
    page = max(1, min(page, total_pages))  # Clamp to valid range
    start = (page - 1) * per_page
    end = start + per_page
    paginated_data = parent_data[start:end]

    return render_template(
        "tab1.html",
        parent_data=paginated_data,
        contract_map=contract_map,
        current_page=page,
        total_pages=total_pages
    )
