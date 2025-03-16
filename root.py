from flask import Blueprint, render_template, redirect, url_for, request
from refresh_logic import refresh_data

root_bp = Blueprint("root", __name__)

@root_bp.route("/")
def home():
    # Render the main dashboard page using index.html
    return render_template("index.html")

@root_bp.route("/manual_refresh", methods=["POST"])
def manual_refresh():
    """
    Refreshes the local database on-demand, then redirects back to home.
    """
    refresh_data()
    return redirect(url_for("root.home"))


