import os
import requests
import sqlite3
import time
from datetime import datetime, timedelta
<<<<<<< HEAD
from config import LOGIN_URL, DB_FILE, SEED_URL, ITEM_MASTER_URL, TRANSACTION_URL, API_PASSWORD, API_USERNAME
=======
from config import DB_FILE

API_USERNAME = os.environ.get("API_USERNAME", "api")
API_PASSWORD = os.environ.get("API_PASSWORD", "Broadway8101")
LOGIN_URL = "https://login.cloud.ptshome.com/api/v1/login"
ITEM_MASTER_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169344381"
TRANSACTION_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169346196"
>>>>>>> 0cd9632179b13a1fd2bf1c588573afce46abb5ed

TOKEN = None
TOKEN_EXPIRY = None
LAST_REFRESH = None
IS_RELOADING = False
REFRESH_INTERVAL = 180  # 180 seconds
STOP_EVENT = None

def init_refresh_state():
    """Initialize refresh_state table and load LAST_REFRESH."""
    global LAST_REFRESH
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refresh_state (
            id INTEGER PRIMARY KEY,
            last_refresh TEXT
        )
    """)
    cursor.execute("SELECT last_refresh FROM refresh_state WHERE id = 1")
    row = cursor.fetchone()
    if row and row[0]:
        LAST_REFRESH = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    else:
        LAST_REFRESH = datetime.utcnow() - timedelta(days=1)  # Default to 24h ago
        cursor.execute("INSERT OR REPLACE INTO refresh_state (id, last_refresh) VALUES (1, ?)", 
                       (LAST_REFRESH.strftime("%Y-%m-%d %H:%M:%S"),))
    conn.commit()
    conn.close()
    print(f"Initialized LAST_REFRESH: {LAST_REFRESH}")

def get_access_token():
    """Fetch and cache API access token."""
    global TOKEN, TOKEN_EXPIRY
    now = datetime.utcnow()

    if TOKEN and TOKEN_EXPIRY and now < TOKEN_EXPIRY:
        return TOKEN

    payload = {"username": API_USERNAME, "password": API_PASSWORD}
    try:
        response = requests.post(LOGIN_URL, json=payload, timeout=10)
        response.raise_for_status()
        TOKEN = response.json().get("access_token")
        TOKEN_EXPIRY = now + timedelta(minutes=55)
        print("Access token refreshed.")
        return TOKEN
    except requests.RequestException as e:
        print(f"Error fetching access token: {e}")
        return None

def fetch_paginated_data(url, token, since_date=None):
    """Fetch data from API with optional date filter."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": 200, "offset": 0}
    if since_date:
        if "item_master" in url:
            params["filter[]"] = f"date_last_scanned>{since_date}"
        elif "transactions" in url:
            params["filter[]"] = f"scan_date>{since_date}"
    all_data = []

    while True:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])
            if not data:
                print(f"Finished fetching {len(all_data)} records from {url}")
                break
            all_data.extend(data)
            print(f"Fetched {len(data)} more records, total: {len(all_data)}")
            params["offset"] += 200
        except requests.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            return all_data
    return all_data

def update_item_master(data):
    """Inserts or updates item master data in SQLite."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    try:
        for item in data:
            cursor.execute(
                """
                INSERT INTO id_item_master (
                    tag_id, uuid_accounts_fk, serial_number, client_name, rental_class_num,
                    common_name, quality, bin_location, status, last_contract_num,
                    last_scanned_by, notes, status_notes, long, lat, date_last_scanned,
                    date_created, date_updated
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tag_id) DO UPDATE SET
                    uuid_accounts_fk = excluded.uuid_accounts_fk,
                    serial_number = excluded.serial_number,
                    client_name = excluded.client_name,
                    rental_class_num = excluded.rental_class_num,
                    common_name = excluded.common_name,
                    quality = excluded.quality,
                    bin_location = excluded.bin_location,
                    status = excluded.status,
                    last_contract_num = excluded.last_contract_num,
                    last_scanned_by = excluded.last_scanned_by,
                    notes = excluded.notes,
                    status_notes = excluded.status_notes,
                    long = excluded.long,
                    lat = excluded.lat,
                    date_last_scanned = excluded.date_last_scanned,
                    date_created = excluded.date_created,
                    date_updated = excluded.date_updated
                """,
                (
                    item.get("tag_id"), item.get("uuid_accounts_fk"), item.get("serial_number"),
                    item.get("client_name"), item.get("rental_class_num"), item.get("common_name"),
                    item.get("quality"), item.get("bin_location"), item.get("status"),
                    item.get("last_contract_num"), item.get("last_scanned_by"), item.get("notes"),
                    item.get("status_notes"), item.get("long"), item.get("lat"),
                    item.get("date_last_scanned"), item.get("date_created"), item.get("date_updated"),
                ),
            )
        conn.commit()
        print("Item Master data updated.")
    except sqlite3.Error as e:
        print(f"Database error updating item master: {e}")
        conn.rollback()
    finally:
        conn.close()

def clear_transactions(conn):
    """Clears all rows from id_transactions before a full refresh."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM id_transactions")
        conn.commit()
        print("Cleared id_transactions table.")
    except sqlite3.Error as e:
        print(f"Error clearing transactions: {e}")
        conn.rollback()

def update_transactions(data):
    """Inserts or updates transaction data in SQLite."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    try:
        for txn in data:
            cursor.execute(
                """
                INSERT INTO id_transactions (
                    contract_number, client_name, tag_id, common_name, bin_location,
                    scan_type, status, scan_date, scan_by, location_of_repair,
                    quality, dirty_or_mud, leaves, oil, mold, stain, oxidation,
                    other, rip_or_tear, sewing_repair_needed, grommet, rope,
                    buckle, date_created, date_updated, uuid_accounts_fk,
                    serial_number, rental_class_num, long, lat, wet,
                    service_required, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(contract_number, tag_id, scan_type, scan_date) DO UPDATE SET
                    client_name = excluded.client_name,
                    common_name = excluded.common_name,
                    bin_location = excluded.bin_location,
                    status = excluded.status,
                    scan_by = excluded.scan_by,
                    location_of_repair = excluded.location_of_repair,
                    quality = excluded.quality,
                    dirty_or_mud = excluded.dirty_or_mud,
                    leaves = excluded.leaves,
                    oil = excluded.oil,
                    mold = excluded.mold,
                    stain = excluded.stain,
                    oxidation = excluded.oxidation,
                    other = excluded.other,
                    rip_or_tear = excluded.rip_or_tear,
                    sewing_repair_needed = excluded.sewing_repair_needed,
                    grommet = excluded.grommet,
                    rope = excluded.rope,
                    buckle = excluded.buckle,
                    date_created = excluded.date_created,
                    date_updated = excluded.date_updated,
                    uuid_accounts_fk = excluded.uuid_accounts_fk,
                    serial_number = excluded.serial_number,
                    rental_class_num = excluded.rental_class_num,
                    long = excluded.long,
                    lat = excluded.lat,
                    wet = excluded.wet,
                    service_required = excluded.service_required,
                    notes = excluded.notes
                """,
                (
                    txn.get("contract_number"), txn.get("client_name"), txn.get("tag_id"),
                    txn.get("common_name"), txn.get("bin_location"), txn.get("scan_type"),
                    txn.get("status"), txn.get("scan_date"), txn.get("scan_by"),
                    txn.get("location_of_repair"), txn.get("quality"), txn.get("dirty_or_mud"),
                    txn.get("leaves"), txn.get("oil"), txn.get("mold"), txn.get("stain"),
                    txn.get("oxidation"), txn.get("other"), txn.get("rip_or_tear"),
                    txn.get("sewing_repair_needed"), txn.get("grommet"), txn.get("rope"),
                    txn.get("buckle"), txn.get("date_created"), txn.get("date_updated"),
                    txn.get("uuid_accounts_fk"), txn.get("serial_number"), txn.get("rental_class_num"),
                    txn.get("long"), txn.get("lat"), txn.get("wet"), txn.get("service_required"),
                    txn.get("notes")
                ),
            )
        conn.commit()
        print("Transaction data updated.")
    except sqlite3.Error as e:
        print(f"Database error updating transactions: {e}")
        conn.rollback()
    finally:
        conn.close()

def update_seed_data(data):
    """Inserts or updates SEED data in SQLite (full refresh only)."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    try:
        for item in data:
            cursor.execute(
                """
                INSERT INTO seed_rental_classes (
                    rental_class_id, common_name, bin_location
                )
                VALUES (?, ?, ?)
                ON CONFLICT(rental_class_id) DO UPDATE SET
                    common_name = excluded.common_name,
                    bin_location = excluded.bin_location
                """,
                (
                    item.get("rental_class_id"), item.get("common_name"), item.get("bin_location"),
                ),
            )
        conn.commit()
        print("SEED data updated.")
    except sqlite3.Error as e:
        print(f"Database error updating SEED data: {e}")
        conn.rollback()
    finally:
        conn.close()

def refresh_data(full_refresh=False):
    """Refresh database: full on demand, incremental otherwise."""
    global LAST_REFRESH, IS_RELOADING
    IS_RELOADING = True
    token = get_access_token()
    if not token:
        print("No access token. Aborting refresh.")
        IS_RELOADING = False
        return

    since_date = None if full_refresh else LAST_REFRESH
    if since_date:
        since_date = since_date.strftime("%Y-%m-%d %H:%M:%S")

    item_master_data = fetch_paginated_data(ITEM_MASTER_URL, token, since_date)
    transactions_data = fetch_paginated_data(TRANSACTION_URL, token, since_date)
    
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    try:
        if full_refresh:
            clear_transactions(conn)
            seed_data = fetch_paginated_data(SEED_URL, token)
            update_seed_data(seed_data)
        update_transactions(transactions_data)
        update_item_master(item_master_data)
        LAST_REFRESH = datetime.utcnow()
        conn.execute("INSERT OR REPLACE INTO refresh_state (id, last_refresh) VALUES (1, ?)", 
                     (LAST_REFRESH.strftime("%Y-%m-%d %H:%M:%S"),))
        conn.commit()
        print(f"Database refreshed at {LAST_REFRESH}")
    except Exception as e:
        print(f"Error during refresh: {e}")
        conn.rollback()
    finally:
        conn.close()
        IS_RELOADING = False

def background_refresh(stop_event):
    """Run incremental refresh every 180 seconds."""
    global STOP_EVENT
    STOP_EVENT = stop_event
    init_refresh_state()  # Load or set LAST_REFRESH
    refresh_data(full_refresh=True)  # Initial full refresh
    while not stop_event.is_set():
        time.sleep(REFRESH_INTERVAL)
        if not stop_event.is_set():
            refresh_data(full_refresh=False)

def trigger_refresh(full=False):
    """Trigger a refresh and reset the timer."""
    global STOP_EVENT
    if STOP_EVENT:
        STOP_EVENT.set()  # Signal the background thread to stop
        time.sleep(1)  # Give it a moment to stop
        STOP_EVENT.clear()  # Reset the event
        refresh_data(full_refresh=full)
        # Restart the background thread
        import threading
        refresher_thread = threading.Thread(target=background_refresh, args=(STOP_EVENT,), daemon=True)
        refresher_thread.start()
        print(f"Triggered {'full' if full else 'incremental'} refresh and reset timer.")