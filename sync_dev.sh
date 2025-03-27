#!/bin/bash
cd /home/tim/test_rfidpi
echo "Starting sync at $(date)" >> /home/tim/test_rfidpi/logs/sync.log
cp config.py config.py.bak 2>> /home/tim/test_rfidpi/logs/sync.log
git pull origin dev_rollback 2>> /home/tim/test_rfidpi/logs/sync.log || { echo "Git pull failed" >> /home/tim/test_rfidpi/logs/sync.log; exit 1; }
mv config.py.bak config.py 2>> /home/tim/test_rfidpi/logs/sync.log
source venv/bin/activate
pip install -r requirements.txt 2>> /home/tim/test_rfidpi/logs/sync.log || { echo "Pip install failed" >> /home/tim/test_rfidpi/logs/sync.log; exit 1; }
sudo systemctl restart rfid_dash_test 2>> /home/tim/test_rfidpi/logs/sync.log || { echo "Service restart failed" >> /home/tim/test_rfidpi/logs/sync.log; exit 1; }
echo "Sync complete at $(date)" >> /home/tim/test_rfidpi/logs/sync.log
