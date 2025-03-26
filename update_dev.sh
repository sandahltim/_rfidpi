#!/bin/bash
cd /home/tim/dev_rfidpi
cp config.py config.py.bak
git pull origin dev
mv config.py.bak config.py
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart rfid_dash_dev
