from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash
from incentive_service import DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes, add_employee, reset_scores, get_history, adjust_points, get_rules, add_rule, get_pot_info, update_pot_info, close_voting_session, get_voting_results
import logging
import time

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "your-secret-key-here"
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

@app.route("/", methods=["GET"])
def show_incentive():
    try:
        with DatabaseConnection() as conn:
            scoreboard = get_scoreboard(conn)
            voting_active = is_voting_active(conn)
            rules = get_rules(conn)
            pot_info = get_pot_info(conn)
            voting_results = get_voting_results(conn) if session.get("admin_id") else []
        logging.debug(f"Loaded incentive page: voting_active={voting_active}, results_count={len(voting_results)}")
        return render_template("incentive.html", scoreboard=scoreboard, voting_active=voting_active, rules=rules, pot_info=pot_info, is_admin=bool(session.get("admin_id")), import_time=int(time.time()), voting_results=voting_results)
    except Exception as e:
        logging.error(f"Error in show_incentive: {str(e)}")
        return "Internal Server Error", 500

@app.route("/data", methods=["GET"])
def incentive_data():
    try:
        with DatabaseConnection() as conn:
            scoreboard = [dict(row) for row in get_scoreboard(conn)]
            voting_active = is_voting_active(conn)
            pot_info = get_pot_info(conn)
        return jsonify({"scoreboard": scoreboard, "voting_active": voting_active, "pot_info": pot_info})
    except Exception as e:
        logging.error(f"Error in incentive_data: {str(e)}")
        return "Internal Server Error", 500

@app.route("/start_voting", methods=["GET", "POST"])
def start_voting():
    if "admin_id" not in session:
        return redirect(url_for("admin"))
    is_master = session.get("admin_id") == "master"
    if request.method == "GET":
        return render_template("start_voting.html", is_master=is_master, import_time=int(time.time()))
    code = request.form.get("vote_code")
    with DatabaseConnection() as conn:
        success, message = start_voting_session(conn, session["admin_id"], code, is_master=is_master)
    logging.debug(f"Start voting: success={success}, message={message}")
    return jsonify({"success": success, "message": message})

@app.route("/close_voting", methods=["POST"])
def close_voting():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    with DatabaseConnection() as conn:
        success, message = close_voting_session(conn, session["admin_id"])
    logging.debug(f"Close voting: success={success}, message={message}")
    return jsonify({"success": success, "message": message})

@app.route("/vote", methods=["POST"])
def vote():
    try:
        voter_initials = request.form.get("initials")
        votes = {key.split("_")[1]: int(value) for key, value in request.form.items() if key.startswith("vote_")}
        with DatabaseConnection() as conn:
            success, message = cast_votes(conn, voter_initials, votes)
        logging.debug(f"Vote cast: initials={voter_initials}, votes={votes}, success={success}, message={message}")
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in vote: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and "username" in request.form:
        username = request.form["username"]
        password = request.form["password"]
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
            if admin and check_password_hash(admin["password"], password):
                session["admin_id"] = admin["admin_id"]
                return redirect(url_for("admin"))
        return render_template("admin_login.html", error="Invalid credentials", import_time=int(time.time()))
    if "admin_id" not in session:
        return render_template("admin_login.html", import_time=int(time.time()))
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, role FROM employees").fetchall()
            rules = get_rules(conn)
            pot_info = get_pot_info(conn)
        return render_template("admin_manage.html", employees=employees, rules=rules, pot_info=pot_info, is_admin=True, import_time=int(time.time()))
    except Exception as e:
        logging.error(f"Error in admin: {str(e)}")
        return "Internal Server Error", 500

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_id", None)
    return redirect(url_for("show_incentive"))

@app.route("/admin/add", methods=["POST"])
def admin_add():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    name = request.form["name"]
    initials = request.form["initials"]
    role = request.form["role"]
    with DatabaseConnection() as conn:
        success, message = add_employee(conn, name, initials, role)
    return jsonify({"success": success, "message": message})

@app.route("/admin/adjust_points", methods=["POST"])
def admin_adjust_points():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    employee_id = request.form["employee_id"]
    points = int(request.form["points"])
    reason = request.form["reason"]
    with DatabaseConnection() as conn:
        success, message = adjust_points(conn, employee_id, points, session["admin_id"], reason)
    return jsonify({"success": success, "message": message})

@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    with DatabaseConnection() as conn:
        success, message = reset_scores(conn, session["admin_id"])
    return jsonify({"success": success, "message": message})

@app.route("/admin/add_rule", methods=["POST"])
def admin_add_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    description = request.form["description"]
    points = int(request.form["points"])
    with DatabaseConnection() as conn:
        success, message = add_rule(conn, description, points)
    return jsonify({"success": success, "message": message})

@app.route("/admin/update_pot", methods=["POST"])
def admin_update_pot():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        sales_dollars = float(request.form["sales_dollars"])
        bonus_percent = float(request.form["bonus_percent"])
        driver_percent = float(request.form["driver_percent"])
        laborer_percent = float(request.form["laborer_percent"])
        supervisor_percent = float(request.form.get("supervisor_percent", 0))
        logging.debug(f"Received pot update: sales_dollars={sales_dollars}, bonus_percent={bonus_percent}, driver_percent={driver_percent}, laborer_percent={laborer_percent}, supervisor_percent={supervisor_percent}")
        with DatabaseConnection() as conn:
            success, message = update_pot_info(conn, sales_dollars, bonus_percent, driver_percent, laborer_percent, supervisor_percent)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in update_pot: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/history", methods=["GET"])
def history():
    month_year = request.args.get("month_year")
    with DatabaseConnection() as conn:
        history = [dict(row) for row in get_history(conn, month_year)]
        months = conn.execute("SELECT DISTINCT month_year FROM score_history ORDER BY month_year DESC").fetchall()
    return render_template("history.html", history=history, months=[m["month_year"] for m in months], is_admin=bool(session.get("admin_id")), import_time=int(time.time()))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6800, debug=True)