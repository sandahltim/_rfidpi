import os
import logging
import time
import threading
from db_utils import initialize_db
from refresh_logic import fast_refresh, full_refresh, FAST_REFRESH_INTERVAL, FULL_REFRESH_INTERVAL
from app import create_app
from werkzeug.serving import is_running_from_reloader

def background_fast_refresh():
    """Run fast refresh every 30 seconds with error handling."""
    while True:
        try:
            fast_refresh()
            time.sleep(FAST_REFRESH_INTERVAL)
        except Exception as e:
            print(f"Fast refresh thread crashed: {e}")
            time.sleep(FAST_REFRESH_INTERVAL)  # Retry after delay

def background_full_refresh():
    """Run full refresh every 5 minutes with error handling."""
    while True:
        try:
            full_refresh()
            time.sleep(FULL_REFRESH_INTERVAL)
        except Exception as e:
            print(f"Full refresh thread crashed: {e}")
            time.sleep(FULL_REFRESH_INTERVAL)  # Retry after delay

# Initialize Flask app globally for Gunicorn
app = create_app()

# Check and initialize DB if needed
db_path = os.path.join(os.path.dirname(__file__), "inventory.db")
if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
    print("Initializing and populating database...")
    initialize_db()
    full_refresh()

# Start background refresh threads only in primary process
if not is_running_from_reloader():
    fast_thread = threading.Thread(target=background_fast_refresh, daemon=True)
    full_thread = threading.Thread(target=background_full_refresh, daemon=True)
    fast_thread.start()
    full_thread.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Starting Flask application...")
    try:
        app.run(host="0.0.0.0", port=8102, debug=True)
    except Exception as e:
        logging.error(f"Flask failed to start: {e}")