import os
import logging
import time
import threading
import sqlite3
from db_utils import initialize_db

from refresh_logic import refresh_data, background_refresh


from app import create_app
from flask import jsonify
from werkzeug.serving import is_running_from_reloader

from config import DB_FILE


app = create_app()
@app.route("/refresh_data", methods=["GET"])
def refresh_data():
    return jsonify({"status": "ok", "message": "Root refresh not implemented"})


# Force full database reload on every restart
db_path = os.path.join(os.path.dirname(__file__), "inventory.db")
print("Forcing full database reload on restart...")
if os.path.exists(db_path):
    os.remove(db_path)  # Delete existing inventory.db
    print(f"Removed existing database: {db_path}")
initialize_db()  # Create fresh schema
refresh_data(full_refresh=True)  # Full API refresh


if not is_running_from_reloader():
    fast_thread = threading.Thread(target=background_fast_refresh, daemon=True)
    full_thread = threading.Thread(target=background_full_refresh, daemon=True)
    fast_thread.start()
    full_thread.start()

if __name__ == "__main__":
    logging.info("Starting Flask application...")
    try:
        app.run(host="0.0.0.0", port=8102, debug=True)
    except Exception as e:
        logging.error(f"Flask failed to start: {e}")
