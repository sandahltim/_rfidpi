import sqlite3
from config import INCENTIVE_DB_FILE
from werkzeug.security import generate_password_hash

def initialize_incentive_db():
    conn = sqlite3.connect(INCENTIVE_DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            initials TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 50,
            role TEXT CHECK(role IN ('driver', 'laborer', 'supervisor'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_initials TEXT,
            recipient_id TEXT,
            vote_value INTEGER CHECK(vote_value IN (-1, 0, 1)),
            vote_date TEXT,
            UNIQUE(voter_initials, recipient_id, vote_date),
            FOREIGN KEY(recipient_id) REFERENCES employees(employee_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voting_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vote_code TEXT,
            admin_id TEXT,
            start_time TEXT,
            end_time TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    admins = [
        ("admin1", "admin1", generate_password_hash("Broadway8101")),
        ("admin2", "admin2", generate_password_hash("Broadway8101")),
        ("admin3", "admin3", generate_password_hash("Broadway8101")),
        ("master", "master", generate_password_hash("Master8101"))
    ]
    cursor.executemany("INSERT OR IGNORE INTO admins (admin_id, username, password) VALUES (?, ?, ?)", admins)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS score_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            changed_by TEXT,
            points INTEGER,
            reason TEXT,
            date TEXT,
            month_year TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incentive_rules (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            points INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incentive_pot (
            id INTEGER PRIMARY KEY,
            sales_dollars REAL DEFAULT 0.0,
            bonus_percent REAL DEFAULT 0.0,
            driver_percent REAL DEFAULT 50.0,
            laborer_percent REAL DEFAULT 50.0,
            supervisor_percent REAL DEFAULT 0.0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO incentive_pot (id, sales_dollars, bonus_percent, driver_percent, laborer_percent, supervisor_percent) VALUES (1, 0.0, 0.0, 50.0, 50.0, 0.0)")

    conn.commit()
    conn.close()
    print("Incentive database initialized at", INCENTIVE_DB_FILE)

if __name__ == "__main__":
    initialize_incentive_db()