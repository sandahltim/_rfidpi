from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
import re

tab6_bp = Blueprint("tab6_bp", __name__, url_prefix="/tab6")

def get_resale_items(conn):
    query = """
       SELECT * FROM id_item_master
       WHERE LOWER(bin_location) = 'resale'
       ORDER BY last_contract_num, tag_id
    """
    return conn.execute(query).fetchall()

# Placeholder for full logic
@tab6_bp.route("/")
def show_tab6():
    print("Loading /tab6/ endpoint")
    return render_template("tab6.html")

@tab6_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    print("Hit /tab6/subcat_data endpoint")
    return jsonify({"items": [], "total_items": 0, "total_pages": 0, "current_page": 1})