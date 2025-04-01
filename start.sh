#!/bin/bash
source venv/bin/activate
gunicorn --workers 2 --bind 0.0.0.0:7409 run:app
