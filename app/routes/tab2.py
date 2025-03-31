from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
import sqlite3

tab2_bp = Blueprint("tab2_bp", __name__, url_prefix="/tab2")

def categorize_item(rental_class_id):
    rid = int(rental_class_id or 0)  # Handle None or invalid
    if 4000 <= rid <= 72412:
        return 'Tent Tops'
    elif 63131 <= rid <= 66555:
        return 'Tables and Chairs'
    elif 61885 <= rid <= 61981:
        return 'Round Linen'
    elif 62088 <= rid <= 62280:
        return 'Rectangle Linen'
    elif 62468 <= rid <= 62654:
        return 'Concession'
    else:
        return 'Other'

def subcategorize_item(category, rental_class_id):
    rid = int(rental_class_id or 0)
    if category == 'Tent Tops':
        if rid == 66456:
            return 'HP Tents'
        elif 4203 <= rid <= 72412:
            return 'Navi Tents'
        else:
            return 'Other Tents'
    elif category == 'Tables and Chairs':
        if 63131 <= rid <= 66548:
            return 'Tables'
        elif rid == 66555:
            return 'Chairs'
        else:
            return 'Other T&C'
    elif category == 'Round Linen':
        if 61885 <= rid <= 61917:
            return '108-inch Round'
        elif 61933 <= rid <= 61981:
            return '120-inch Round'
        elif 61982 <= rid <= 62035:
            return '132-inch Round'
        else:
            return 'Other Round Linen'
    elif category == 'Rectangle Linen':
        if 62291 <= rid <= 62339:
            return '54 Square'
        elif 62088 <= rid <= 62142:
            return '60x120'
        elif 62187 <= rid <= 62231:
            return '90x132'
        elif 62235 <= rid <= 62280:
            return '90x156'
        else:
            return 'Other Rectangle Linen'
    elif category == 'Concession':
        if 62468 <= rid <= 62654:
            return 'Equipment'
        else:
            return 'Other Concessions'
    else:
        return 'Unspecified Subcategory'

@tab2_bp.route("/")
def show_tab2():
    print("Loading /tab2/ endpoint")
    with DatabaseConnection() as conn:
        items = conn.execute("SELECT * FROM id_item_master").fetchall()
        contracts = conn.execute("SELECT DISTINCT last_contract_num, client_name, MAX(date_last_scanned) as scan_date FROM id_item_master WHERE last_contract_num IS NOT NULL GROUP BY last_contract_num").fetchall()
    items = [dict(row) for row in items]
    contract_map = {c["last_contract_num"]: {"client_name": c["client_name"], "scan_date": c["scan_date"]} for c in contracts}

    filter_common_name = request.args.get("common_name", "").lower().strip()
    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    filtered_items = items
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in (item.get("common_name") or "").lower()]
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if filter_tag_id in (item.get("tag_id") or "").lower()]
    if filter_bin_location:
        filtered_items = [item for item in filtered_items if filter_bin_location in (item.get("bin_location") or "").lower()]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if filter_last_contract in (item.get("last_contract_num") or "").lower()]
    if filter_status:
        filtered_items = [item for item in filtered_items if filter_status in (item.get("status") or "").lower()]

    category_map = defaultdict(list)
    for item in filtered_items:
        cat = categorize_item(item.get("rental_class_num"))
        category_map[cat].append(item)

    parent_data = []
    sub_map = {}
    for category, item_list in category_map.items():
        available = sum(1 for item in item_list if item["status"] == "Ready to Rent")
        on_rent = sum(1 for item in item_list if item["status"] in ["On Rent", "Delivered"])
        service = len(item_list) - available - on_rent
        client_name = contract_map.get(item_list[0]["last_contract_num"], {}).get("client_name", "N/A") if item_list and item_list[0]["last_contract_num"] else "N/A"
        scan_date = contract_map.get(item_list[0]["last_contract_num"], {}).get("scan_date", "N/A") if item_list and item_list[0]["last_contract_num"] else "N/A"

        temp_sub_map = defaultdict(list)
        for itm in item_list:
            subcat = subcategorize_item(category, itm.get("rental_class_num"))
            temp_sub_map[subcat].append(itm)

        sub_map[category] = {
            "subcategories": {subcat: {"total": len(items)} for subcat, items in temp_sub_map.items()}
        }

        parent_data.append({
            "category": category,
            "total": len(item_list),
            "available": available,
            "on_rent": on_rent,
            "service": service,
            "client_name": client_name,
            "scan_date": scan_date
        })

    parent_data.sort(key=lambda x: x["category"])
    expand_category = request.args.get('expand', None)

    return render_template(
        "tab2.html",
        parent_data=parent_data,
        sub_map=sub_map,
        expand_category=expand_category,
        filter_common_name=filter_common_name,
        filter_tag_id=filter_tag_id,
        filter_bin_location=filter_bin_location,
        filter_last_contract=filter_last_contract,
        filter_status=filter_status
    )

@tab2_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    print("Hit /tab2/subcat_data endpoint")
    category = request.args.get('category')
    subcat = request.args.get('subcat')
    page = int(request.args.get('page', 1))
    per_page = 20

    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master").fetchall()
    items = [dict(row) for row in rows]

    filter_common_name = request.args.get("common_name", "").lower().strip()
    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    filtered_items = items
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in (item.get("common_name") or "").lower()]
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if filter_tag_id in (item.get("tag_id") or "").lower()]
    if filter_bin_location:
        filtered_items = [item for item in filtered_items if filter_bin_location in (item.get("bin_location") or "").lower()]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if filter_last_contract in (item.get("last_contract_num") or "").lower()]
    if filter_status:
        filtered_items = [item for item in filtered_items if filter_status in (item.get("status") or "").lower()]

    category_items = [item for item in filtered_items if categorize_item(item.get("rental_class_num")) == category]
    subcat_items = [item for item in category_items if subcategorize_item(category, item.get("rental_class_num")) == subcat]

    total_items = len(subcat_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = subcat_items[start:end]

    print(f"AJAX: Category: {category}, Subcategory: {subcat}, Total Items: {total_items}, Page: ${page}")

    return jsonify({
        "items": [{
            "tag_id": item["tag_id"],
            "common_name": item["common_name"],
            "status": item["status"],
            "bin_location": item.get("bin_location", "N/A"),
            "quality": item.get("quality", "N/A"),
            "last_contract_num": item.get("last_contract_num", "N/A"),
            "date_last_scanned": item.get("date_last_scanned", "N/A"),
            "last_scanned_by": item.get("last_scanned_by", "N/A"),
            "notes": item.get("notes", "N/A")
        } for item in paginated_items],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    })