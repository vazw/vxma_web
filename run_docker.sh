#!/bin/bash
export TERM=xterm

source /env/bin/activate
gunicorn --bind "0.0.0.0:8050" web_app:server --workers 1 &
python app.py
