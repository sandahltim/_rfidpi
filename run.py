import os
import time
import threading
from db_utils import initialize_db
from refresh_logic import fast_refresh, full_refresh, FAST_REFRESH_INTERVAL, FULL_REFRESH_INTERVAL
from app import create_app
from flask import jsonify
from werkzeug.serving import is_running_from_reloader

def background_fast_refresh():
    while True:
        try:
            fast_refresh()
            time.sleep(FAST_REFRESH_INTERVAL)
        except Exception:
            # Silently ignore errors to avoid debug/log output
            time.sleep(FAST_REFRESH_INTERVAL)

def background_full_refresh():
    while True:
        try:
            full_refresh()
            time.sleep(FULL_REFRESH_INTERVAL)
        except Exception:
            # Silently ignore errors to avoid debug/log output
            time.sleep(FULL_REFRESH_INTERVAL)

app = create_app()

@app.route("/refresh_data", methods=["GET"])
def refresh_data():
    return jsonify({"status": "ok", "message": "Root refresh not implemented"})

db_path = os.path.join(os.path.dirname(__file__), "inventory.db")
if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
    initialize_db()
    full_refresh()

if not is_running_from_reloader():
    fast_thread = threading.Thread(target=background_fast_refresh, daemon=True)
    full_thread = threading.Thread(target=background_full_refresh, daemon=True)
    fast_thread.start()
    full_thread.start()

if __name__ == "__main__":
    try:
        # Removed debug=True to strip out development-mode logging
        app.run(host="0.0.0.0", port=8101)
    except Exception:
        # Silently ignore errors to avoid debug/log output
        pass
