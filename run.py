import os
import logging
import time
import threading
import sqlite3
from datetime import datetime
from db_utils import initialize_db
from refresh_logic import refresh_data, background_refresh
from app import create_app
from werkzeug.serving import is_running_from_reloader
from config import DB_FILE, INCENTIVE_DB_FILE
from incentive_db_utils import initialize_incentive_db
from incentive_service import reset_scores, DatabaseConnection as IncentiveDBConnection

app = create_app()

# Ensure directory is writable and initialize inventory.db
db_path = os.path.join(os.path.dirname(__file__), "inventory.db")
print("Forcing full database reload on restart...")
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Removed existing database: {db_path}")
os.chmod(os.path.dirname(db_path), 0o775)  # Ensure directory is writable
initialize_db()  # Create fresh schema
refresh_data(full_refresh=True)

# Initialize incentive.db
incentive_db_path = INCENTIVE_DB_FILE
print("Initializing incentive.db...")
if not os.path.exists(incentive_db_path):
    initialize_incentive_db()
    print(f"Created new incentive database: {incentive_db_path}")

def check_monthly_reset():
    now = datetime.now()
    with IncentiveDBConnection(INCENTIVE_DB_FILE) as conn:
        cursor = conn.execute("SELECT MAX(date) FROM score_history WHERE reason LIKE 'Monthly reset%'")
        last_reset = cursor.fetchone()[0]
        if not last_reset or datetime.strptime(last_reset, "%Y-%m-%d %H:%M:%S").month != now.month:
            reset_scores(conn, "system", reason=f"Monthly reset for {now.strftime('%Y-%m')}")
            print(f"Performed monthly reset for {now.strftime('%Y-%m')}")

if not is_running_from_reloader():
    refresher_thread = threading.Thread(target=background_refresh, daemon=True)
    refresher_thread.start()
    check_monthly_reset()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Starting Flask application...")
    try:
        app.run(host="0.0.0.0", port=7409, debug=True)
    except Exception as e:
        logging.error(f"Flask failed to start: {e}")