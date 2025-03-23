#!/bin/bash
cd /home/tim/test_rfidpi

# Stash SCP’d files
git stash push -m "Save SCP’d config and refresh_logic" config.py refresh_logic.py

# Pull latest from dev
git fetch origin
git checkout dev
git pull origin dev

# Reapply SCP’d files
git stash pop

# Restart service
sudo systemctl restart rfid_dash_test

echo "Sync complete: $(git rev-parse HEAD)"