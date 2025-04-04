#!/bin/bash
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:6800 app:app