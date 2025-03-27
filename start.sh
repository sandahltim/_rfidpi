#!/bin/bash
source /home/tim/test_rfidpi/venv/bin/activate
gunicorn --workers 2 --bind 0.0.0.0:8102 --access-logfile /home/tim/test_rfidpi/logs/gunicorn_access.log --error-logfile /home/tim/test_rfidpi/logs/gunicorn_error.log --log-level debug --capture-output --enable-stdio-inheritance run:app
