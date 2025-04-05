import sqlite3
from datetime import datetime, timedelta
from config import INCENTIVE_DB_FILE
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
    return conn.execute("""
        SELECT e.employee_id, e.name, e.initials, e.score, LOWER(r.role_name) AS role
        FROM employees e
        JOIN roles r ON e.role = LOWER(r.role_name)
        WHERE e.active = 1
        ORDER BY e.score DESC
    """).fetchall()

def start_voting_session(conn, admin_id):
    now = datetime.now()
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time > ? OR end_time IS NULL",
        (now.strftime("%Y-%m-%d %H:%M:%S"),)
    ).fetchone()
    if active_session:
        return False, "Voting session already active or paused"
    start_time = now.strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO voting_sessions (vote_code, admin_id, start_time, end_time) VALUES (?, ?, ?, NULL)",
        ("active", admin_id, start_time)
    )
    logging.debug(f"Voting session started: admin_id={admin_id}, start={start_time}")
    return True, "Voting session started"

def close_voting_session(conn, admin_id):
    now = datetime.now()
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time IS NULL"
    ).fetchone()
    if not active_session:
        return False, "No active voting session to close"
    start_time = active_session["start_time"]
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    votes = conn.execute(
        "SELECT voter_initials, recipient_id, vote_value FROM votes WHERE vote_date >= ? AND vote_date <= ?",
        (start_time, now.strftime("%Y-%m-%d %H:%M:%S"))
    ).fetchall()
    logging.debug(f"Closing session: {len(votes)} votes found between {start_time} and {end_time}")
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
        if plus_percent >= 20:
            points += 5
        elif plus_percent >= 10:
            points += 3
        elif plus_percent >= 5:
            points += 1
        if minus_percent >= 20:
            points -= 5
        elif minus_percent >= 10:
            points -= 3
        elif minus_percent >= 5:
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

def pause_voting_session(conn, admin_id):
    now = datetime.now()
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time IS NULL"
    ).fetchone()
    if not active_session:
        return False, "No active voting session to pause"
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE voting_sessions SET end_time = ? WHERE session_id = ?", (end_time, active_session["session_id"]))
    logging.debug(f"Voting session paused: admin_id={admin_id}, end_time={end_time}")
    return True, "Voting session paused"

def is_voting_active(conn):
    now = datetime.now()
    session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time IS NULL"
    ).fetchone()
    if not session:
        return False
    eligible_voters = conn.execute("SELECT COUNT(*) as count FROM employees").fetchone()["count"]
    votes_cast = conn.execute(
        "SELECT COUNT(DISTINCT voter_initials) as count FROM votes WHERE vote_date >= ?",
        (session["start_time"],)
    ).fetchone()["count"]
    return votes_cast < eligible_voters

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

    plus_votes = sum(1 for value in votes.values() if value > 0)
    minus_votes = sum(1 for value in votes.values() if value < 0)
    total_votes = plus_votes + minus_votes
    
    if plus_votes > 2:
        return False, "You can only cast up to 2 positive (+1) votes per session"
    if minus_votes > 3:
        return False, "You can only cast up to 3 negative (-1) votes per session"
    if total_votes > 3:
        return False, "You can only cast a maximum of 3 votes total per session"

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
    role_lower = role.lower()  # Normalize to lowercase for employees table
    conn.execute(
        "INSERT INTO employees (employee_id, name, initials, score, role, active) VALUES (?, ?, ?, 50, ?, 1)",
        (employee_id, name, initials, role_lower)
    )
    return True, f"Employee {name} added with ID {employee_id}"

def retire_employee(conn, employee_id):
    conn.execute(
        "UPDATE employees SET active = 0 WHERE employee_id = ?",
        (employee_id,)
    )
    affected = conn.total_changes
    return affected > 0, f"Employee {employee_id} retired" if affected > 0 else "Employee not found"

def reactivate_employee(conn, employee_id):
    conn.execute(
        "UPDATE employees SET active = 1 WHERE employee_id = ?",
        (employee_id,)
    )
    affected = conn.total_changes
    return affected > 0, f"Employee {employee_id} reactivated" if affected > 0 else "Employee not found"

def delete_employee(conn, employee_id):
    conn.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
    affected = conn.total_changes
    return affected > 0, f"Employee {employee_id} permanently deleted" if affected > 0 else "Employee not found"

def edit_employee(conn, employee_id, name, role):
    role_lower = role.lower()  # Normalize to lowercase for employees table
    conn.execute(
        "UPDATE employees SET name = ?, role = ? WHERE employee_id = ?",
        (name, role_lower, employee_id)
    )
    affected = conn.total_changes
    return affected > 0, f"Employee {employee_id} updated" if affected > 0 else "Employee not found"

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

def master_reset_all(conn):
    conn.execute("DELETE FROM votes")
    conn.execute("DELETE FROM score_history")
    conn.execute("DELETE FROM voting_sessions")
    conn.execute("UPDATE employees SET score = 50")
    logging.debug("Master reset: cleared votes, history, sessions, reset scores to 50")
    return True, "All voting data and history reset"

def get_history(conn, month_year=None):
    query = "SELECT sh.*, e.name FROM score_history sh JOIN employees e ON sh.employee_id = e.employee_id"
    params = []
    if month_year:
        query += " WHERE month_year = ?"
        params.append(month_year)
    query += " ORDER BY date DESC"
    return conn.execute(query, params).fetchall()

def get_rules(conn):
    try:
        return conn.execute("SELECT description, points FROM incentive_rules ORDER BY display_order ASC").fetchall()
    except sqlite3.OperationalError as e:
        if "no such column: display_order" in str(e):
            logging.warning("display_order column missing, falling back to unordered fetch")
            return conn.execute("SELECT description, points FROM incentive_rules").fetchall()
        raise

def add_rule(conn, description, points):
    try:
        max_order = conn.execute("SELECT MAX(display_order) as max_order FROM incentive_rules").fetchone()["max_order"] or 0
        conn.execute(
            "INSERT INTO incentive_rules (description, points, display_order) VALUES (?, ?, ?)",
            (description, points, max_order + 1)
        )
    except sqlite3.OperationalError as e:
        if "no such column: display_order" in str(e):
            conn.execute(
                "INSERT INTO incentive_rules (description, points) VALUES (?, ?)",
                (description, points)
            )
        else:
            raise
    return True, f"Rule '{description}' added with {points} points"

def edit_rule(conn, old_description, new_description, points):
    conn.execute(
        "UPDATE incentive_rules SET description = ?, points = ? WHERE description = ?",
        (new_description, points, old_description)
    )
    affected = conn.total_changes
    return affected > 0, f"Rule '{old_description}' updated to '{new_description}' with {points} points" if affected > 0 else "Rule not found"

def remove_rule(conn, description):
    conn.execute(
        "DELETE FROM incentive_rules WHERE description = ?",
        (description,)
    )
    affected = conn.total_changes
    return affected > 0, f"Rule '{description}' removed" if affected > 0 else "Rule not found"

def reorder_rules(conn, order):
    try:
        for index, description in enumerate(order):
            conn.execute(
                "UPDATE incentive_rules SET display_order = ? WHERE description = ?",
                (index + 1, description)
            )
        return True, "Rules reordered successfully"
    except sqlite3.OperationalError as e:
        if "no such column: display_order" in str(e):
            logging.warning("display_order column missing, reordering not supported")
            return False, "Rule reordering not available due to missing display_order column"
        raise

def get_roles(conn):
    try:
        return conn.execute("SELECT role_name, percentage FROM roles").fetchall()
    except sqlite3.OperationalError:
        logging.warning("roles table missing, returning default roles with supervisor")
        conn.execute("CREATE TABLE roles (role_name TEXT PRIMARY KEY, percentage REAL)")
        conn.execute("INSERT INTO roles (role_name, percentage) VALUES ('driver', 50)")
        conn.execute("INSERT INTO roles (role_name, percentage) VALUES ('laborer', 45)")
        conn.execute("INSERT INTO roles (role_name, percentage) VALUES ('supervisor', 5)")
        return conn.execute("SELECT role_name, percentage FROM roles").fetchall()
      
def add_role(conn, role_name, percentage):
    roles = get_roles(conn)
    if len(roles) >= 10:
        return False, "Maximum number of roles reached"
    total_percentage = sum(role["percentage"] for role in roles) + percentage
    if total_percentage > 100:
        return False, "Total percentage exceeds 100%"
    role_name_lower = role_name.lower()
    conn.execute(
        "INSERT INTO roles (role_name, percentage) VALUES (?, ?)",
        (role_name, percentage)
    )
    # Update any existing employees with this role to lowercase (if applicable)
    conn.execute(
        "UPDATE employees SET role = ? WHERE role = ?",
        (role_name_lower, role_name)
    )
    return True, f"Role '{role_name}' added with {percentage}%"

def edit_role(conn, old_role_name, new_role_name, percentage):
    roles = get_roles(conn)
    total_percentage = sum(role["percentage"] for role in roles if role["role_name"] != old_role_name) + percentage
    if total_percentage > 100:
        return False, f"Total percentage cannot exceed 100%, got {total_percentage}% after edit"
    # Normalize new_role_name to lowercase for employees table
    new_role_name_lower = new_role_name.lower()
    conn.execute(
        "UPDATE roles SET role_name = ?, percentage = ? WHERE role_name = ?",
        (new_role_name, percentage, old_role_name)
    )
    conn.execute(
        "UPDATE employees SET role = ? WHERE role = ?",
        (new_role_name_lower, old_role_name)
    )
    affected = conn.total_changes
    return affected > 0, f"Role '{old_role_name}' updated to '{new_role_name}' with {percentage}% (Total: {total_percentage}%)" if affected > 0 else "Role not found"


def remove_role(conn, role_name):
    if role_name == "supervisor":
        return False, "Cannot remove the 'supervisor' role as it is required for voting weight and admin functionality"
    roles = get_roles(conn)
    if len(roles) <= 2:
        return False, "Cannot remove role; minimum of 2 roles (excluding supervisor) required"
    conn.execute("DELETE FROM roles WHERE role_name = ?", (role_name,))
    affected = conn.total_changes
    if affected > 0:
        conn.execute("UPDATE employees SET role = 'driver' WHERE role = ?", (role_name,))
        return True, f"Role '{role_name}' removed, affected employees reassigned to 'driver'"
    return False, "Role not found"

def get_pot_info(conn):
    pot_row = conn.execute("SELECT sales_dollars, bonus_percent FROM incentive_pot WHERE id = 1").fetchone()
    pot = dict(pot_row) if pot_row else {"sales_dollars": 0.0, "bonus_percent": 0.0}
    roles = get_roles(conn)
    for role in roles:
        role_name = role["role_name"].lower()  # Normalize to lowercase
        pot[f"{role_name}_percent"] = role["percentage"]
        pot[f"{role_name}_pot"] = 0.0
        pot[f"{role_name}_point_value"] = 0.0

    total_pot = pot["sales_dollars"] * pot["bonus_percent"] / 100
    for role in roles:
        role_name = role["role_name"].lower()  # Normalize to lowercase
        role_percent = pot[f"{role_name}_percent"]
        role_pot = total_pot * role_percent / 100
        role_count = conn.execute("SELECT COUNT(*) as count FROM employees WHERE role = ? AND active = 1", (role_name,)).fetchone()["count"] or 1
        max_points_per_employee = 100
        role_max_points = role_count * max_points_per_employee
        role_point_value = role_pot / role_max_points if role_max_points > 0 else 0
        pot[f"{role_name}_pot"] = role_pot
        pot[f"{role_name}_point_value"] = role_point_value

    logging.debug(f"Pot info retrieved: {pot}")
    return pot

def update_pot_info(conn, sales_dollars, bonus_percent, percentages):
    roles = get_roles(conn)
    total_role_percentage = sum(percentages.values())
    if total_role_percentage != 100:
        return False, f"Total role percentages must equal 100%, got {total_role_percentage}%"
    if len(roles) != len(percentages):
        return False, "Percentage must be provided for each role"
    for role in roles:
        role_name = role["role_name"]
        if role_name not in percentages:
            return False, f"Percentage for role '{role_name}' missing"
        conn.execute(
            "UPDATE roles SET percentage = ? WHERE role_name = ?",
            (percentages[role_name], role_name)
        )
    conn.execute(
        "INSERT OR REPLACE INTO incentive_pot (id, sales_dollars, bonus_percent) VALUES (1, ?, ?)",
        (sales_dollars, bonus_percent)
    )
    return True, "Pot info updated"

def get_voting_results(conn, is_admin=False, week_number=None):
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
    end_of_month = (now.replace(day=1, month=now.month+1) - timedelta(days=1)).replace(hour=23, minute=59, second=59).strftime("%Y-%m-%d %H:%M:%S")

    if is_admin and week_number:
        week_start = (now.replace(day=1) + timedelta(weeks=week_number-1)).strftime("%Y-%m-%d 00:00:00")
        week_end = (datetime.strptime(week_start, "%Y-%m-%d %H:%M:%S") + timedelta(days=6)).strftime("%Y-%m-%d 23:59:59")
        query = """
            SELECT v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date, sh.points
            FROM votes v
            JOIN employees e ON v.recipient_id = e.employee_id
            LEFT JOIN score_history sh ON v.recipient_id = sh.employee_id AND sh.reason LIKE 'Weekly vote result%' AND sh.date >= ? AND sh.date <= ?
            WHERE v.vote_date >= ? AND v.vote_date <= ?
            ORDER BY v.vote_date DESC
        """
        params = [week_start, week_end, week_start, week_end]
    elif is_admin:
        last_session = conn.execute(
            "SELECT start_time, end_time FROM voting_sessions ORDER BY end_time DESC LIMIT 1"
        ).fetchone()
        if not last_session:
            logging.debug("No voting sessions found")
            return []
        start_date = last_session["start_time"]
        end_date = last_session["end_time"] or now.strftime("%Y-%m-%d %H:%M:%S")
        query = """
            SELECT v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date, sh.points
            FROM votes v
            JOIN employees e ON v.recipient_id = e.employee_id
            LEFT JOIN score_history sh ON v.recipient_id = sh.employee_id AND sh.reason LIKE 'Weekly vote result%' AND sh.date >= ? AND sh.date <= ?
            WHERE v.vote_date >= ? AND v.vote_date <= ?
            ORDER BY v.vote_date DESC
        """
        params = [start_date, end_date, start_date, end_date]
    else:
        query = """
            SELECT strftime('%W', v.vote_date) as week_number, e.name AS recipient_name,
                   SUM(CASE WHEN v.vote_value > 0 THEN v.vote_value ELSE 0 END) as plus_votes,
                   SUM(CASE WHEN v.vote_value < 0 THEN -v.vote_value ELSE 0 END) as minus_votes, sh.points
            FROM votes v
            JOIN employees e ON v.recipient_id = e.employee_id
            LEFT JOIN score_history sh ON v.recipient_id = sh.employee_id AND sh.reason LIKE 'Weekly vote result%' AND sh.date >= ? AND sh.date <= ?
            WHERE v.vote_date >= ? AND v.vote_date <= ?
            GROUP BY strftime('%W', v.vote_date), e.name, sh.points
            ORDER BY week_number DESC
        """
        params = [start_of_month, end_of_month, start_of_month, end_of_month]

    results = conn.execute(query, params).fetchall()
    logging.debug(f"Voting results fetched: {len(results)} entries for {'admin' if is_admin else 'non-admin'} view")
    return [dict(row) for row in results]