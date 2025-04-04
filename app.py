from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash
from incentive_service import DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes, add_employee, reset_scores, get_history

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "your-secret-key-here"  # Replace with a secure key

@app.route("/", methods=["GET"])
def show_incentive():
    with DatabaseConnection() as conn:
        scoreboard = get_scoreboard(conn)
        voting_active = is_voting_active(conn)
    return render_template("incentive.html", scoreboard=scoreboard, voting_active=voting_active)

@app.route("/data", methods=["GET"])
def incentive_data():
    with DatabaseConnection() as conn:
        scoreboard = [dict(row) for row in get_scoreboard(conn)]
        voting_active = is_voting_active(conn)
    return jsonify({"scoreboard": scoreboard, "voting_active": voting_active})

@app.route("/start_voting", methods=["GET", "POST"])
def start_voting():
    if "admin_id" not in session:
        return redirect(url_for("admin"))
    if request.method == "GET":
        return render_template("start_voting.html")
    code = request.form.get("vote_code")
    with DatabaseConnection() as conn:
        success, message = start_voting_session(conn, session["admin_id"], code)
    return jsonify({"success": success, "message": message})

@app.route("/vote", methods=["POST"])
def vote():
    voter_initials = request.form.get("initials")
    votes = {key.split("_")[1]: int(value) for key, value in request.form.items() if key.startswith("vote_")}
    with DatabaseConnection() as conn:
        success, message = cast_votes(conn, voter_initials, votes)
    return jsonify({"success": success, "message": message})

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
        return render_template("admin_login.html", error="Invalid credentials")
    if "admin_id" not in session:
        return render_template("admin_login.html")
    return render_template("admin_manage.html")

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

@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    with DatabaseConnection() as conn:
        success, message = reset_scores(conn, session["admin_id"])
    return jsonify({"success": success, "message": message})

@app.route("/history", methods=["GET"])
def history():
    month_year = request.args.get("month_year")
    with DatabaseConnection() as conn:
        history = [dict(row) for row in get_history(conn, month_year)]
        months = conn.execute("SELECT DISTINCT month_year FROM score_history ORDER BY month_year DESC").fetchall()
    return render_template("history.html", history=history, months=[m["month_year"] for m in months])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6800, debug=True)