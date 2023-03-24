#!/bin/bash
export TERM=xterm

# gunicorn --certfile cert.pem --keyfile key.pem -b 0.0.0.0:8000 hello:app
gunicorn --certfile cert.pem --keyfile key.pem --bind "0.0.0.0:8050" web_app:server --workers 1 &
python app.py
