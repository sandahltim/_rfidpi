import sqlite3
from datetime import datetime, timedelta
from config import INCENTIVE_DB_FILE, VOTING_DAYS_2025

class DatabaseConnection:
    def __enter__(self):
        self.conn = sqlite3.connect(INCENTIVE_DB_FILE)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

def get_scoreboard(conn):
    return conn.execute("SELECT employee_id, name, initials, score, role FROM employees ORDER BY score DESC").fetchall()

def start_voting_session(conn, admin_id, code, is_master=False):
    from config import VOTE_CODE
    now = datetime.now()
    if not is_master:
        if now.weekday() not in [2, 3, 4]:  # Wed (2), Thu (3), Fri (4)
            return False, "Voting only allowed Wednesday through Friday"
    if code != VOTE_CODE:
        return False, "Invalid voting code"
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time > ?",
        (now.strftime("%Y-%m-%d %H:%M:%S"),)
    ).fetchone()
    if active_session:
        return False, "Voting session already active"
    start_time = now.strftime("%Y-%m-%d %H:%M:%S")
    # Set end time to Friday 11:59 PM of current week
    days_to_friday = (4 - now.weekday()) % 7
    end_time = (now + timedelta(days=days_to_friday)).replace(hour=23, minute=59, second=59).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO voting_sessions (vote_code, admin_id, start_time, end_time) VALUES (?, ?, ?, ?)",
        (code, admin_id, start_time, end_time)
    )
    return True, "Voting session started until Friday 11:59 PM"

def close_voting_session(conn, admin_id):
    now = datetime.now()
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time > ?",
        (now.strftime("%Y-%m-%d %H:%M:%S"),)
    ).fetchone()
    if not active_session:
        return False, "No active voting session to close"
    week_number = datetime.strptime(active_session["start_time"], "%Y-%m-%d %H:%M:%S").isocalendar()[1]
    votes = conn.execute(
        "SELECT voter_initials, recipient_id, vote_value FROM votes WHERE vote_date >= ? AND vote_date <= ?",
        (active_session["start_time"], active_session["end_time"])
    ).fetchall()
    employees = {e["employee_id"]: e for e in conn.execute("SELECT employee_id, role, score FROM employees").fetchall()}
    vote_counts = {}
    total_votes = 0
    for vote in votes:
        voter = conn.execute("SELECT role FROM employees WHERE initials = ?", (vote["voter_initials"],)).fetchone()
        weight = 2 if voter and voter["role"] == "supervisor" else 1
        total_votes += weight
        recipient_id = vote["recipient_id"]
        if recipient_id not in vote_counts:
            vote_counts[recipient_id] = {"plus": 0, "minus": 0}
        if vote["vote_value"] > 0:
            vote_counts[recipient_id]["plus"] += weight
        elif vote["vote_value"] < 0:
            vote_counts[recipient_id]["minus"] += weight

    for emp_id, counts in vote_counts.items():
        plus_percent = (counts["plus"] / total_votes) * 100 if total_votes > 0 else 0
        minus_percent = (counts["minus"] / total_votes) * 100 if total_votes > 0 else 0
        points = 0
        if plus_percent >= 100:
            points += 10
        elif plus_percent >= 75:
            points += 7
        elif plus_percent >= 50:
            points += 5
        elif plus_percent >= 25:
            points += 3
        if minus_percent >= 100:
            points -= 10
        elif minus_percent >= 75:
            points -= 7
        elif minus_percent >= 50:
            points -= 5
        elif minus_percent >= 25:
            points -= 3
        if points != 0 and emp_id in employees:
            old_score = employees[emp_id]["score"]
            new_score = min(100, max(0, old_score + points))
            conn.execute(
                "UPDATE employees SET score = ? WHERE employee_id = ?",
                (new_score, emp_id)
            )
            conn.execute(
                "INSERT INTO score_history (employee_id, changed_by, points, reason, date, month_year) VALUES (?, ?, ?, ?, ?, ?)",
                (emp_id, admin_id, points, f"Weekly vote result: {counts['plus']} +1, {counts['minus']} -1", now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"))
            )

    conn.execute("UPDATE voting_sessions SET end_time = ? WHERE session_id = ?", (now.strftime("%Y-%m-%d %H:%M:%S"), active_session["session_id"]))
    return True, f"Voting session closed, scores updated based on {total_votes} votes"

def is_voting_active(conn):
    now = datetime.now()
    session = conn.execute(
        "SELECT * FROM voting_sessions WHERE start_time <= ? AND end_time > ?",
        (now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"))
    ).fetchone()
    return bool(session and now.weekday() in [2, 3, 4])

def cast_votes(conn, voter_initials, votes):
    now = datetime.now()
    voter = conn.execute("SELECT employee_id, role FROM employees WHERE initials = ?", (voter_initials,)).fetchone()
    if not voter:
        return False, "Invalid voter initials"
    if not is_voting_active(conn):
        return False, "Voting is not active"
    week_number = now.isocalendar()[1]
    existing_vote = conn.execute(
        "SELECT COUNT(*) as count FROM votes WHERE voter_initials = ? AND strftime('%W', vote_date) = ?",
        (voter_initials, str(week_number))
    ).fetchone()["count"]
    if existing_vote > 0:
        return False, "You have already voted this week"
    
    for recipient_id, vote_value in votes.items():
        if recipient_id not in conn.execute("SELECT employee_id FROM employees").fetchall():
            continue
        conn.execute(
            "INSERT INTO votes (voter_initials, recipient_id, vote_value, vote_date) VALUES (?, ?, ?, ?)",
            (voter_initials, recipient_id, vote_value, now.strftime("%Y-%m-%d %H:%M:%S"))
        )
    return True, "Votes cast successfully"

def add_employee(conn, name, initials, role):
    employee_id = f"E{str(len(conn.execute('SELECT * FROM employees').fetchall()) + 1).zfill(3)}"
    conn.execute(
        "INSERT INTO employees (employee_id, name, initials, score, role) VALUES (?, ?, ?, 50, ?)",
        (employee_id, name, initials, role)
    )
    return True, f"Employee {name} added with ID {employee_id}"

def adjust_points(conn, employee_id, points, admin_id, reason):
    now = datetime.now()
    employee = conn.execute("SELECT score FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
    if not employee:
        return False, "Employee not found"
    new_score = min(100, max(0, employee["score"] + points))
    conn.execute(
        "UPDATE employees SET score = ? WHERE employee_id = ?",
        (new_score, employee_id)
    )
    conn.execute(
        "INSERT INTO score_history (employee_id, changed_by, points, reason, date, month_year) VALUES (?, ?, ?, ?, ?, ?)",
        (employee_id, admin_id, points, reason, now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"))
    )
    return True, f"Adjusted {points} points for employee {employee_id}"

def reset_scores(conn, admin_id, reason=None):
    now = datetime.now()
    employees = conn.execute("SELECT employee_id, score FROM employees").fetchall()
    for emp in employees:
        if emp["score"] != 50:
            conn.execute(
                "INSERT INTO score_history (employee_id, changed_by, points, reason, date, month_year) VALUES (?, ?, ?, ?, ?, ?)",
                (emp["employee_id"], admin_id, 50 - emp["score"], reason or "Manual reset", now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"))
            )
    conn.execute("UPDATE employees SET score = 50")
    return True, "Scores reset to 50"

def get_history(conn, month_year=None):
    query = "SELECT * FROM score_history"
    params = []
    if month_year:
        query += " WHERE month_year = ?"
        params.append(month_year)
    query += " ORDER BY date DESC"
    return conn.execute(query, params).fetchall()

def get_rules(conn):
    return conn.execute("SELECT description, points FROM incentive_rules ORDER BY points DESC").fetchall()

def add_rule(conn, description, points):
    conn.execute(
        "INSERT INTO incentive_rules (description, points) VALUES (?, ?)",
        (description, points)
    )
    return True, f"Rule '{description}' added with {points} points"

def get_pot_info(conn):
    pot = conn.execute("SELECT * FROM incentive_pot WHERE id = 1").fetchone()
    if not pot:
        return {
            "sales_dollars": 0.0, "bonus_percent": 0.0, "driver_percent": 50.0, "laborer_percent": 50.0,
            "driver_pot": 0.0, "laborer_pot": 0.0, "driver_point_value": 0.0, "laborer_point_value": 0.0
        }
    total_pot = pot["sales_dollars"] * pot["bonus_percent"] / 100
    driver_pot = total_pot * pot["driver_percent"] / 100
    laborer_pot = total_pot * pot["laborer_percent"] / 100
    driver_count = conn.execute("SELECT COUNT(*) as count FROM employees WHERE role = 'driver'").fetchone()["count"] or 1
    laborer_count = conn.execute("SELECT COUNT(*) as count FROM employees WHERE role = 'laborer'").fetchone()["count"] or 1
    max_points_per_employee = 100
    driver_max_points = driver_count * max_points_per_employee
    laborer_max_points = laborer_count * max_points_per_employee
    driver_point_value = driver_pot / driver_max_points if driver_max_points > 0 else 0
    laborer_point_value = laborer_pot / laborer_max_points if laborer_max_points > 0 else 0
    return {
        "sales_dollars": pot["sales_dollars"], "bonus_percent": pot["bonus_percent"],
        "driver_percent": pot["driver_percent"], "laborer_percent": pot["laborer_percent"],
        "driver_pot": driver_pot, "laborer_pot": laborer_pot,
        "driver_point_value": driver_point_value, "laborer_point_value": laborer_point_value
    }

def update_pot_info(conn, sales_dollars, bonus_percent, driver_percent, laborer_percent):
    if driver_percent + laborer_percent != 100:
        return False, "Driver and Laborer percentages must sum to 100%"
    conn.execute(
        "INSERT OR REPLACE INTO incentive_pot (id, sales_dollars, bonus_percent, driver_percent, laborer_percent) VALUES (1, ?, ?, ?, ?)",
        (sales_dollars, bonus_percent, driver_percent, laborer_percent)
    )
    return True, "Pot info updated"