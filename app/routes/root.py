from flask import Blueprint, render_template, redirect, url_for, request

root_bp = Blueprint("root", __name__)

@root_bp.route("/")
def home():
    return render_template("index.html")

@root_bp.route("/manual_refresh", methods=["POST"])
def manual_refresh():
    return redirect(url_for("full_refresh"))

@root_bp.route("/manual_refresh_dev", methods=["POST"])
def manual_refresh_dev():
    return redirect(url_for("full_refresh"))