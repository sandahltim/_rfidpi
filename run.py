import os
import logging
import time
import threading
from db_utils import initialize_db
from refresh_logic import refresh_data
from app import create_app
from werkzeug.serving import is_running_from_reloader

def background_refresh():
    """
    Continuously refresh data every 10 minutes.
    Runs in a separate thread so the Flask app remains responsive.
    """
    while True:
        refresh_data()
        print("⏳ Waiting 10 minutes before next update...")
        time.sleep(600)

def main():
    # Check if inventory.db is missing or empty. If so, initialize and populate it.
    db_path = os.path.join(os.path.dirname(__file__), "inventory.db")
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        print("Initializing and populating database...")
        initialize_db()
        refresh_data()

    app = create_app()

    # Only start the background refresh thread in the primary process (avoid double-fetch in debug mode)
    if not is_running_from_reloader():
        refresher_thread = threading.Thread(target=background_refresh, daemon=True)
        refresher_thread.start()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Starting Flask application...")

    try:
        # Run Flask in debug mode so code changes auto-reload, but data is only refreshed once.
        app.run(host="0.0.0.0", port=8101, debug=True)
    except Exception as e:
        logging.error(f"Flask failed to start: {e}")

if __name__ == "__main__":
    main()



