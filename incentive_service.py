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

def start_voting_session(conn, admin_id, code):
    from config import VOTE_CODE
    now = datetime.now()
    if now.weekday() != 2 or now.strftime("%Y-%m-%d") not in VOTING_DAYS_2025:
        return False, "Voting only allowed on designated Wednesdays"
    if code != VOTE_CODE:
        return False, "Invalid voting code"
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE start_time <= ? AND end_time >= ?",
        (now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"))
    ).fetchone()
    if active_session:
        return False, "Voting session already active"
    start_time = now.strftime("%Y-%m-%d %H:%M:%S")
    end_time = (now + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO voting_sessions (vote_code, admin_id, start_time, end_time) VALUES (?, ?, ?, ?)",
        (code, admin_id, start_time, end_time)
    )
    return True, "Voting session started"

def is_voting_active(conn):
    now = datetime.now()
    if now.weekday() != 2 or now.strftime("%Y-%m-%d") not in VOTING_DAYS_2025:
        return False
    session = conn.execute(
        "SELECT * FROM voting_sessions WHERE start_time <= ? AND end_time >= ?",
        (now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"))
    ).fetchone()
    return bool(session)

def cast_votes(conn, voter_initials, votes):
    now = datetime.now()
    voter = conn.execute("SELECT initials FROM employees WHERE initials = ?", (voter_initials,)).fetchone()
    if not voter:
        return False, "Invalid voter initials"
    if not is_voting_active(conn):
        return False, "Voting is not active"
    today = now.strftime("%Y-%m-%d")
    existing_votes = conn.execute(
        "SELECT recipient_id FROM votes WHERE voter_initials = ? AND vote_date LIKE ?",
        (voter_initials, f"{today}%")
    ).fetchall()
    if existing_votes:
        return False, "You have already voted today"
    
    for recipient_id, vote_value in votes.items():
        employee = conn.execute("SELECT score FROM employees WHERE employee_id = ?", (recipient_id,)).fetchone()
        if not employee:
            continue
        new_score = min(100, max(0, employee["score"] + vote_value))
        conn.execute(
            "UPDATE employees SET score = ? WHERE employee_id = ?",
            (new_score, recipient_id)
        )
        conn.execute(
            "INSERT INTO score_history (employee_id, changed_by, points, reason, date, month_year) VALUES (?, ?, ?, ?, ?, ?)",
            (recipient_id, voter_initials, vote_value, f"Vote by {voter_initials}", now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"))
        )
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
        return {"sales_dollars": 0.0, "bonus_percent": 0.0, "driver_percent": 50.0, "laborer_percent": 50.0, "point_value": 0.0}
    total_points = conn.execute("SELECT SUM(score) as total FROM employees WHERE role IN ('driver', 'laborer')").fetchone()["total"] or 1
    total_pot = pot["sales_dollars"] * pot["bonus_percent"] / 100
    point_value = total_pot / total_points if total_points > 0 else 0
    return {"sales_dollars": pot["sales_dollars"], "bonus_percent": pot["bonus_percent"], "driver_percent": pot["driver_percent"], "laborer_percent": pot["laborer_percent"], "point_value": point_value}

def update_pot_info(conn, sales_dollars, bonus_percent, driver_percent, laborer_percent):
    if driver_percent + laborer_percent != 100:
        return False, "Driver and Laborer percentages must sum to 100%"
    conn.execute(
        "INSERT OR REPLACE INTO incentive_pot (id, sales_dollars, bonus_percent, driver_percent, laborer_percent) VALUES (1, ?, ?, ?, ?)",
        (sales_dollars, bonus_percent, driver_percent, laborer_percent)
    )
    return True, "Pot info updated"