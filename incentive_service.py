import sqlite3
from datetime import datetime, timedelta
from config import INCENTIVE_DB_FILE, VOTING_DAYS_2025
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

class DatabaseConnection:
    def __enter__(self):
        self.conn = sqlite3.connect(INCENTIVE_DB_FILE)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
            logging.error(f"DB rollback due to {exc_type}: {exc_val}")
        else:
            self.conn.commit()
        self.conn.close()

def get_scoreboard(conn):
    return conn.execute("SELECT employee_id, name, initials, score, role FROM employees ORDER BY score DESC").fetchall()

def start_voting_session(conn, admin_id, code, is_master=False):
    from config import VOTE_CODE
    now = datetime.now()
    if not is_master:
        if now.weekday() not in [2, 3, 4]:
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
    days_to_friday = (4 - now.weekday()) % 7
    end_time = (now + timedelta(days=days_to_friday)).replace(hour=23, minute=59, second=59).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO voting_sessions (vote_code, admin_id, start_time, end_time) VALUES (?, ?, ?, ?)",
        (code, admin_id, start_time, end_time)
    )
    logging.debug(f"Voting session started: admin_id={admin_id}, start={start_time}, end={end_time}")
    return True, "Voting session started until Friday 11:59 PM"

def close_voting_session(conn, admin_id):
    now = datetime.now()
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time > ?",
        (now.strftime("%Y-%m-%d %H:%M:%S"),)
    ).fetchone()
    if not active_session:
        return False, "No active voting session to close"
    start_time = active_session["start_time"]
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    votes = conn.execute(
        "SELECT voter_initials, recipient_id, vote_value FROM votes WHERE vote_date >= ? AND vote_date <= ?",
        (start_time, active_session["end_time"])
    ).fetchall()
    logging.debug(f"Closing session: {len(votes)} votes found between {start_time} and {active_session['end_time']}")
    employees = {e["employee_id"]: dict(e) for e in conn.execute("SELECT employee_id, name, role, score FROM employees").fetchall()}
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

    logging.debug(f"Total votes calculated: {total_votes}")
    for emp_id, counts in vote_counts.items():
        if emp_id not in employees:
            logging.warning(f"Employee ID {emp_id} not found in employees table")
            continue
        plus_percent = (counts["plus"] / total_votes) * 100 if total_votes > 0 else 0
        minus_percent = (counts["minus"] / total_votes) * 100 if total_votes > 0 else 0
        points = 0
        if plus_percent >= 50:
            points += 5
        elif plus_percent >= 20:
            points += 3
        elif plus_percent >= 10:
            points += 1
        if minus_percent >= 50:
            points -= 5
        elif minus_percent >= 20:
            points -= 3
        elif minus_percent >= 10:
            points -= 1
        logging.debug(f"Employee {emp_id} ({employees[emp_id]['name']}): plus={counts['plus']} ({plus_percent}%), minus={counts['minus']} ({minus_percent}%), points={points}")
        if points != 0:
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
            logging.debug(f"Updated score: emp_id={emp_id}, name={employees[emp_id]['name']}, old_score={old_score}, new_score={new_score}, points={points}")

    conn.execute("UPDATE voting_sessions SET end_time = ? WHERE session_id = ?", (end_time, active_session["session_id"]))
    logging.debug(f"Voting session closed: total_votes={total_votes}")
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
        if not conn.execute("SELECT 1 FROM employees WHERE employee_id = ?", (recipient_id,)).fetchone():
            logging.warning(f"Invalid recipient_id: {recipient_id}")
            continue
        conn.execute(
            "INSERT INTO votes (voter_initials, recipient_id, vote_value, vote_date) VALUES (?, ?, ?, ?)",
            (voter_initials, recipient_id, vote_value, now.strftime("%Y-%m-%d %H:%M:%S"))
        )
        logging.debug(f"Vote recorded: voter={voter_initials}, recipient={recipient_id}, value={vote_value}")
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
        (new_score, emp_id)
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
    query = "SELECT sh.*, e.name FROM score_history sh JOIN employees e ON sh.employee_id = e.employee_id"
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
    pot_row = conn.execute("SELECT * FROM incentive_pot WHERE id = 1").fetchone()
    pot = dict(pot_row) if pot_row else {}
    defaults = {
        "sales_dollars": 0.0, "bonus_percent": 0.0, "driver_percent": 50.0, "laborer_percent": 50.0, "supervisor_percent": 0.0,
        "driver_pot": 0.0, "laborer_pot": 0.0, "supervisor_pot": 0.0, "driver_point_value": 0.0, "laborer_point_value": 0.0, "supervisor_point_value": 0.0
    }
    pot = {**defaults, **pot}
    total_pot = pot["sales_dollars"] * pot["bonus_percent"] / 100
    driver_pot = total_pot * pot["driver_percent"] / 100
    laborer_pot = total_pot * pot["laborer_percent"] / 100
    supervisor_pot = total_pot * pot["supervisor_percent"] / 100
    driver_count = conn.execute("SELECT COUNT(*) as count FROM employees WHERE role = 'driver'").fetchone()["count"] or 1
    laborer_count = conn.execute("SELECT COUNT(*) as count FROM employees WHERE role = 'laborer'").fetchone()["count"] or 1
    supervisor_count = conn.execute("SELECT COUNT(*) as count FROM employees WHERE role = 'supervisor'").fetchone()["count"] or 1
    max_points_per_employee = 100
    driver_max_points = driver_count * max_points_per_employee
    laborer_max_points = laborer_count * max_points_per_employee
    supervisor_max_points = supervisor_count * max_points_per_employee
    driver_point_value = driver_pot / driver_max_points if driver_max_points > 0 else 0
    laborer_point_value = laborer_pot / laborer_max_points if laborer_max_points > 0 else 0
    supervisor_point_value = supervisor_pot / supervisor_max_points if supervisor_max_points > 0 else 0
    pot.update({
        "driver_pot": driver_pot, "laborer_pot": laborer_pot, "supervisor_pot": supervisor_pot,
        "driver_point_value": driver_point_value, "laborer_point_value": laborer_point_value, "supervisor_point_value": supervisor_point_value
    })
    return pot

def update_pot_info(conn, sales_dollars, bonus_percent, driver_percent, laborer_percent, supervisor_percent):
    if driver_percent + laborer_percent + supervisor_percent != 100:
        return False, "Driver, Laborer, and Supervisor percentages must sum to 100%"
    conn.execute(
        "INSERT OR REPLACE INTO incentive_pot (id, sales_dollars, bonus_percent, driver_percent, laborer_percent, supervisor_percent) VALUES (1, ?, ?, ?, ?, ?)",
        (sales_dollars, bonus_percent, driver_percent, laborer_percent, supervisor_percent)
    )
    return True, "Pot info updated"

def get_voting_results(conn):
    now = datetime.now()
    last_session = conn.execute(
        "SELECT start_time, end_time FROM voting_sessions ORDER BY end_time DESC LIMIT 1"
    ).fetchone()
    if not last_session:
        logging.debug("No voting sessions found")
        return []
    start_date = last_session["start_time"]
    end_date = last_session["end_time"]
    results = conn.execute("""
        SELECT v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date, sh.points
        FROM votes v
        JOIN employees e ON v.recipient_id = e.employee_id
        LEFT JOIN score_history sh ON v.recipient_id = sh.employee_id AND sh.reason LIKE 'Weekly vote result%' AND sh.date >= ? AND sh.date <= ?
        WHERE v.vote_date >= ? AND v.vote_date <= ?
        ORDER BY v.vote_date DESC
    """, (start_date, end_date, start_date, end_date)).fetchall()
    logging.debug(f"Voting results fetched: {len(results)} entries between {start_date} and {end_date}")
    return [dict(row) for row in results]