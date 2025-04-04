import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "inventory.db")
INCENTIVE_DB_FILE = os.path.join(BASE_DIR, "incentive.db")  # New DB

API_USERNAME = os.environ.get("API_USERNAME", "api")
API_PASSWORD = os.environ.get("API_PASSWORD", "Broadway8101")
LOGIN_URL = "https://login.cloud.ptshome.com/api/v1/login"
ITEM_MASTER_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169344381"
TRANSACTION_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169346196"
SEED_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169215907"

# Voting days for 2025 (Wednesdays: June 4, 11, 18, 25; Aug 6, 13, 20, 27; Sept 3, 10, 17, 24)
VOTING_DAYS_2025 = [
    "2025-06-04", "2025-06-11", "2025-06-18", "2025-06-25",
    "2025-08-06", "2025-08-13", "2025-08-20", "2025-08-27",
    "2025-09-03", "2025-09-10", "2025-09-17", "2025-09-24"
]
VOTE_CODE = "VOTE2025"