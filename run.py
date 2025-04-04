import os
import logging
import threading
from datetime import datetime
from app import create_app
from db_utils import initialize_db
from incentive_db_utils import initialize_incentive_db
from refresh_logic import background_refresh, refresh_data
from werkzeug.serving import is_running_from_reloader
from config import DB_FILE, INCENTIVE_DB_FILE
from incentive_service import reset_scores

# Initialize Flask app
app = create_app()

# Force full database reload for inventory.db on restart
db_path = DB_FILE
print("Forcing full database reload for inventory.db on restart...")
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Removed existing database: {db_path}")
initialize_db()
refresh_data(full_refresh=True)

# Initialize incentive.db
incentive_db_path = INCENTIVE_DB_FILE
print("Initializing incentive.db...")
if not os.path.exists(incentive_db_path):
    initialize_incentive_db()
    print(f"Created new incentive database: {incentive_db_path}")

# Check and reset scores on startup if new month
def check_monthly_reset():
    from incentive_service import DatabaseConnection
    now = datetime.now()
    with DatabaseConnection(INCENTIVE_DB_FILE) as conn:
        cursor = conn.execute("SELECT MAX(date) FROM score_history WHERE reason LIKE 'Monthly reset%'")
        last_reset = cursor.fetchone()[0]
        if not last_reset or datetime.strptime(last_reset, "%Y-%m-%d %H:%M:%S").month != now.month:
            reset_scores(conn, "system", reason=f"Monthly reset for {now.strftime('%Y-%m')}")
            print(f"Performed monthly reset for {now.strftime('%Y-%m')}")

# Start background refresh thread for inventory.db
if not is_running_from_reloader():
    stop_event = threading.Event()
    refresher_thread = threading.Thread(target=background_refresh, args=(stop_event,), daemon=True)
    refresher_thread.start()
    check_monthly_reset()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Starting Flask application...")
    try:
        app.run(host="0.0.0.0", port=7409, debug=True)
    except Exception as e:
        logging.error(f"Flask failed to start: {e}")