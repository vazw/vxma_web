#!/bin/bash
export TERM=xterm

gunicorn --bind "0.0.0.0:8050" web_app:server --workers 1 &
python app.py
