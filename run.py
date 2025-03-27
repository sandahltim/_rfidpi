import os
import logging
import time
import threading
import sys
from db_utils import initialize_db
from refresh_logic import fast_refresh, full_refresh, FAST_REFRESH_INTERVAL, FULL_REFRESH_INTERVAL
from app import create_app
from flask import jsonify
from werkzeug.serving import is_running_from_reloader

# Setup logging to /tmp
try:
    logging.basicConfig(
        filename='/tmp/rfid_dash_test.log',  # Move to /tmp
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)
    logger.debug("Logging initialized")
except Exception as e:
    print(f"Logging setup failed: {e}")
    sys.exit(1)

# Get Flask's logger
try:
    flask_logger = logging.getLogger('werkzeug')
    flask_logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler('/tmp/rfid_dash_test.log')  # Move to /tmp
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    flask_logger.addHandler(handler)
except Exception as e:
    print(f"Flask logger setup failed: {e}")
    sys.exit(1)

def background_fast_refresh():
    logger.debug("Starting fast refresh thread")
    while True:
        try:
            fast_refresh()
            time.sleep(FAST_REFRESH_INTERVAL)
        except Exception as e:
            logger.error(f"Fast refresh thread crashed: {e}", exc_info=True)
            time.sleep(FAST_REFRESH_INTERVAL)

def background_full_refresh():
    logger.debug("Starting full refresh thread")
    while True:
        try:
            full_refresh()
            time.sleep(FULL_REFRESH_INTERVAL)
        except Exception as e:
            logger.error(f"Full refresh thread crashed: {e}", exc_info=True)
            time.sleep(FULL_REFRESH_INTERVAL)

try:
    app = create_app()
    logger.debug("Flask app created")
except Exception as e:
    print(f"App creation failed: {e}")
    sys.exit(1)

@app.route("/refresh_data", methods=["GET"])
def refresh_data():
    return jsonify({"status": "ok", "message": "Root refresh not implemented"})

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return "Internal Server Error", 500

db_path = os.path.join(os.path.dirname(__file__), "inventory.db")
try:
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        logger.info("Initializing and populating database...")
        initialize_db()
        full_refresh()
except Exception as e:
    print(f"Database init failed: {e}")
    sys.exit(1)

def start_background_threads():
    if not is_running_from_reloader():
        try:
            fast_thread = threading.Thread(target=background_fast_refresh, daemon=True)
            full_thread = threading.Thread(target=background_full_refresh, daemon=True)
            fast_thread.start()
            full_thread.start()
            logger.debug("Background threads started")
        except Exception as e:
            logger.error(f"Thread start failed: {e}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8102)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        logger.info(f"Starting Flask on {args.host}:{args.port}, debug={args.debug}")
        start_background_threads()  # Start threads after Flask setup
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        logger.error(f"Flask failed to start: {e}", exc_info=True)
        sys.exit(1)