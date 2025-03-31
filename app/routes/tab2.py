from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
import re

tab2_bp = Blueprint("tab2_bp", __name__, url_prefix="/tab2")

def tokenize_name(name):
    return re.split(r'\W+', name.lower())

def categorize_item(item):
    tokens = tokenize_name(item.get("common_name", ""))
    if any(word in tokens for word in ['tent', 'canopy', 'pole', 'hp', 'mid', 'end', 'navi']):
        return 'Tent Tops'
    elif any(word in tokens for word in ['table', 'chair', 'plywood', 'prong']):
        return 'Tables and Chairs'
    elif any(word in tokens for word in ['132', '120', '90', '108']):
        return 'Round Linen'
    elif any(word in tokens for word in ['90x90', '90x132', '60x120', '90x156', '54']):
        return 'Rectangle Linen'
    elif any(word in tokens for word in ['otc', 'machine', 'hotdog', 'warmer']):
        return 'Concession'
    else:
        return 'Other'

def subcategorize_item(category, item):
    tokens = tokenize_name(item.get("common_name", ""))
    if category == 'Tent Tops':
        if any(word in tokens for word in ['hp']):
            return 'HP Tents'
        elif any(word in tokens for word in ['ncp', 'nc', 'end', 'pole']):
            return 'Pole Tents'
        elif any(word in tokens for word in ['navi']):
            return 'Navi Tents'
        elif any(word in tokens for word in ['canopy']):
            return 'AP Tents'
        else:
            return item.get("common_name", "Other Tents")
    elif category == 'Tables and Chairs':
        if 'table' in tokens:
            return 'Tables'
        elif 'chair' in tokens:
            return 'Chairs'
        else:
            return item.get("common_name", "Other T&C")
    elif category == 'Round Linen':
        if '90' in tokens:
            return '90-inch Round'
        elif '108' in tokens:
            return '108-inch Round'
        elif '120' in tokens:
            return '120-inch Round'
        elif '132' in tokens:
            return '132-inch Round'
        else:
            return item.get("common_name", "Other Round Linen")
    elif category == 'Rectangle Linen':
        if '90x90' in tokens:
            return '90 Square'
        elif '54' in tokens:
            return '54 Square'
        elif '90x132' in tokens:
            return '90x132'
        elif '90x156' in tokens:
            return '90x156'
        elif '60x120' in tokens:
            return '60x120'
        else:
            return item.get("common_name", "Other Rectangle Linen")
    elif category == 'Concession':
        if 'frozen' in tokens:
            return 'Frozen Drink Machines'
        elif 'cotton' in tokens:
            return 'Cotton Candy Machines'
        elif 'sno' in tokens:
            return 'SnoKone Machines'
        elif 'hotdog' in tokens:
            return 'Hotdog Machines'
        elif 'warmer' in tokens:
            return 'Warmers'
        elif 'popcorn' in tokens:
            return 'Popcorn Machines'
        else:
            return item.get("common_name", "Other Concessions")
    else:
        return item.get("common_name", "Other Items")

@tab2_bp.route("/")
def show_tab2():
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
        filtered_items = [
            item for item in filtered_items 
            if filter_common_name in (item.get("common_name") or "").lower()
        ]
    if filter_tag_id:
        filtered_items = [
            item for item in filtered_items 
            if filter_tag_id in (item.get("tag_id") or "").lower()
        ]
    if filter_bin_location:
        filtered_items = [
            item for item in filtered_items 
            if filter_bin_location in (item.get("bin_location") or "").lower()
        ]
    if filter_last_contract:
        filtered_items = [
            item for item in filtered_items 
            if filter_last_contract in (item.get("last_contract_num") or "").lower()
        ]
    if filter_status:
        filtered_items = [
            item for item in filtered_items 
            if filter_status in (item.get("status") or "").lower()
        ]

    category_map = defaultdict(list)
    for item in filtered_items:
        cat = categorize_item(item)
        category_map[cat].append(item)

    parent_data = []
    sub_map = {}
    middle_map = {}
    expand_category = request.args.get('expand', None)
    selected_subcat = request.args.get('subcat', None)

    for category, item_list in category_map.items():
        available = sum(1 for i in item_list if i["status"] == "Ready to Rent")
        on_rent = sum(1 for i in item_list if i["status"] in ["On Rent", "Delivered"])
        service = sum(1 for i in item_list if i["status"] not in ["Ready to Rent", "On Rent", "Delivered"])
        total = len(item_list)

        temp_sub_map = defaultdict(list)
        for itm in item_list:
            subcat = subcategorize_item(category, itm)
            temp_sub_map[subcat].append(itm)
        sub_map[category] = {"subcategories": list(temp_sub_map.keys())}

        common_name_map = defaultdict(list)
        for itm in item_list:
            cname = itm.get("common_name", "Unknown")
            common_name_map[cname].append(itm)
        middle_map[category] = [
            {"common_name": n, "total": len(i)}
            for n, i in sorted(common_name_map.items(), key=lambda x: x[0].lower())
        ]

        subcat_to_show = (
            selected_subcat 
            if selected_subcat in temp_sub_map 
            else (list(temp_sub_map.keys())[0] if temp_sub_map else None)
        )
        display_middle_map = {}
        if subcat_to_show:
            cat_items = temp_sub_map[subcat_to_show]
            display_common_name_map = defaultdict(list)
            for itm in cat_items:
                cname = itm.get("common_name", "Unknown")
                display_common_name_map[cname].append(itm)
            display_middle_map[category] = [
                {"common_name": n, "total": len(i)}
                for n, i in sorted(display_common_name_map.items(), key=lambda x: x[0].lower())
            ]

        parent_data.append({
            "category": category,
            "total": total,
            "available": available,
            "on_rent": on_rent,
            "service": service
        })

    parent_data.sort(key=lambda x: x["category"])

    return render_template(
        "tab2.html",
        parent_data=parent_data,
        middle_map=middle_map,
        display_middle_map=display_middle_map,
        sub_map=sub_map,
        expand_category=expand_category,
        selected_subcat=selected_subcat,
        filter_common_name=filter_common_name,
        filter_tag_id=filter_tag_id,
        filter_bin_location=filter_bin_location,
        filter_last_contract=filter_last_contract,
        filter_status=filter_status
    )

@tab2_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    category = request.args.get('category')
    subcat = request.args.get('subcat')
    common_name = request.args.get('common_name')
    page = int(request.args.get('page', 1))
    per_page = 20

    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master").fetchall()
    items = [dict(row) for row in rows]

    filter_common_name = request.args.get("common_name_filter", "").lower().strip()
    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    filtered_items = items
    if filter_common_name:
        filtered_items = [
            i for i in filtered_items 
            if filter_common_name in (i.get("common_name") or "").lower()
        ]
    if filter_tag_id:
        filtered_items = [
            i for i in filtered_items 
            if filter_tag_id in (i.get("tag_id") or "").lower()
        ]
    if filter_bin_location:
        filtered_items = [
            i for i in filtered_items 
            if filter_bin_location in (i.get("bin_location") or "").lower()
        ]
    if filter_last_contract:
        filtered_items = [
            i for i in filtered_items 
            if filter_last_contract in (i.get("last_contract_num") or "").lower()
        ]
    if filter_status:
        filtered_items = [
            i for i in filtered_items 
            if filter_status in (i.get("status") or "").lower()
        ]

    category_items = [i for i in filtered_items if categorize_item(i) == category]
    subcat_items = [i for i in category_items if subcategorize_item(category, i) == subcat]
    if common_name:
        subcat_items = [i for i in subcat_items if i.get("common_name", "Unknown") == common_name]

    total_items = len(subcat_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = subcat_items[start:end]

    return jsonify({
        "items": [{
            "tag_id": itm["tag_id"],
            "common_name": itm["common_name"],
            "status": itm["status"],
            "bin_location": itm["bin_location"],
            "quality": itm["quality"]
        } for itm in paginated_items],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    })

@tab2_bp.route("/middle_data", methods=["GET"])
def middle_data():
    category = request.args.get('category')
    subcat = request.args.get('subcat')

    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master").fetchall()
    items = [dict(row) for row in rows]

    filter_common_name = request.args.get("common_name_filter", "").lower().strip()
    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    filtered_items = items
    if filter_common_name:
        filtered_items = [
            i for i in filtered_items 
            if filter_common_name in (i.get("common_name") or "").lower()
        ]
    if filter_tag_id:
        filtered_items = [
            i for i in filtered_items 
            if filter_tag_id in (i.get("tag_id") or "").lower()
        ]
    if filter_bin_location:
        filtered_items = [
            i for i in filtered_items 
            if filter_bin_location in (i.get("bin_location") or "").lower()
        ]
    if filter_last_contract:
        filtered_items = [
            i for i in filtered_items 
            if filter_last_contract in (i.get("last_contract_num") or "").lower()
        ]
    if filter_status:
        filtered_items = [
            i for i in filtered_items 
            if filter_status in (i.get("status") or "").lower()
        ]

    category_items = [i for i in filtered_items if categorize_item(i) == category]
    subcat_items = [i for i in category_items if subcategorize_item(category, i) == subcat]

    common_name_map = defaultdict(list)
    for itm in subcat_items:
        cname = itm.get("common_name", "Unknown")
        common_name_map[cname].append(itm)

    middle_data = [
        {"common_name": n, "total": len(i)}
        for n, i in sorted(common_name_map.items(), key=lambda x: x[0].lower())
    ]

    return jsonify({"middle_data": middle_data})
