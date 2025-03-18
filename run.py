import os
import logging
import time
import threading
from db_utils import initialize_db
from refresh_logic import refresh_data
from app import create_app
from werkzeug.serving import is_running_from_reloader

def background_refresh():
    """Continuously refresh data every 10 minutes."""
    while True:
        refresh_data()
        print("Waiting 10 minutes before next update...")
        time.sleep(600)

# Initialize Flask app globally for Gunicorn
app = create_app()

# Check and initialize DB if needed
db_path = os.path.join(os.path.dirname(__file__), "inventory.db")
if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
    print("Initializing and populating database...")
    initialize_db()
    refresh_data()

# Start background refresh thread only in primary process
if not is_running_from_reloader():
    refresher_thread = threading.Thread(target=background_refresh, daemon=True)
    refresher_thread.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Starting Flask application...")
    try:
        app.run(host="0.0.0.0", port=8102, debug=True)
    except Exception as e:
        logging.error(f"Flask failed to start: {e}")
