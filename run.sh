#!/bin/bash

gunicorn --bind "0.0.0.0:8050" web_app:server --workers 1 &
python app.py
# cron */30 * * * * python /path/to/app.py
