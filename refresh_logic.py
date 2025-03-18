import os
import requests
import sqlite3
import time
from datetime import datetime, timedelta
from config import DB_FILE

API_USERNAME = os.environ.get("API_USERNAME", "api")
API_PASSWORD = os.environ.get("API_PASSWORD", "Broadway8101")
LOGIN_URL = "https://login.cloud.ptshome.com/api/v1/login"
ITEM_MASTER_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169344381"
TRANSACTION_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169346196"

TOKEN = None
TOKEN_EXPIRY = None

def get_access_token():
    """Fetch and cache API access token."""
    global TOKEN, TOKEN_EXPIRY
    now = datetime.utcnow()

    if TOKEN and TOKEN_EXPIRY and now < TOKEN_EXPIRY:
        return TOKEN

    payload = {"api": API_USERNAME, "Broadway8101": API_PASSWORD}
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

def fetch_paginated_data(url, token):
    """Fetch all data from the given API endpoint using pagination."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": 200, "offset": 0}
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
            print(f" Fetched {len(data)} more records, total: {len(all_data)}")
            params["offset"] += 200
        except requests.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            return all_data
    return all_data

def update_item_master(data):
    """Inserts or updates item master data in SQLite, using all columns."""
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
                    item.get("tag_id"),
                    item.get("uuid_accounts_fk"),
                    item.get("serial_number"),
                    item.get("client_name"),
                    item.get("rental_class_num"),
                    item.get("common_name"),
                    item.get("quality"),
                    item.get("bin_location"),
                    item.get("status"),
                    item.get("last_contract_num"),
                    item.get("last_scanned_by"),
                    item.get("notes"),
                    item.get("status_notes"),
                    item.get("long"),
                    item.get("lat"),
                    item.get("date_last_scanned"),
                    item.get("date_created"),
                    item.get("date_updated"),
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
    """Clears all rows from id_transactions before a refresh."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM id_transactions")
        conn.commit()
        print(" Cleared id_transactions table.")
    except sqlite3.Error as e:
        print(f" Error clearing transactions: {e}")
        conn.rollback()

def update_transactions(data):
    """Inserts or updates transaction data in SQLite after clearing old data."""
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
                    txn.get("contract_number"),
                    txn.get("client_name"),
                    txn.get("tag_id"),
                    txn.get("common_name"),
                    txn.get("bin_location"),
                    txn.get("scan_type"),
                    txn.get("status"),
                    txn.get("scan_date"),
                    txn.get("scan_by"),
                    txn.get("location_of_repair"),
                    txn.get("quality"),
                    txn.get("dirty_or_mud"),
                    txn.get("leaves"),
                    txn.get("oil"),
                    txn.get("mold"),
                    txn.get("stain"),
                    txn.get("oxidation"),
                    txn.get("other"),
                    txn.get("rip_or_tear"),
                    txn.get("sewing_repair_needed"),
                    txn.get("grommet"),
                    txn.get("rope"),
                    txn.get("buckle"),
                    txn.get("date_created"),
                    txn.get("date_updated"),
                    txn.get("uuid_accounts_fk"),
                    txn.get("serial_number"),
                    txn.get("rental_class_num"),
                    txn.get("long"),
                    txn.get("lat"),
                    txn.get("wet"),
                    txn.get("service_required"),
                    txn.get("notes")
                ),
            )
        conn.commit()
        print("Transaction data updated.")
    except sqlite3.Error as e:
        print(f" Database error updating transactions: {e}")
        conn.rollback()
    finally:
        conn.close()

def refresh_data():
    """Main function to refresh item master and transaction data from the API."""
    token = get_access_token()
    if not token:
        print(" No access token. Aborting refresh.")
        return

    item_master_data = fetch_paginated_data(ITEM_MASTER_URL, token)
    transactions_data = fetch_paginated_data(TRANSACTION_URL, token)

    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    try:
        clear_transactions(conn)
        update_transactions(transactions_data)
        update_item_master(item_master_data)
    finally:
        conn.close()

    print("Waiting 10 minutes before next update...")
