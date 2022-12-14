#!/bin/bash
# checking if we have env
export TERM=xterm
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d $DIR/env ]]; then
    python -m virtualenv env
    python -m pip install -r requirements.txt
    python vxma_d/AppData/ResetDatabase.py
fi

source env/bin/activate
gunicorn --bind "0.0.0.0:8050" web_app:server --workers 1 &
python app.py
# cron */30 * * * * python /path/to/app.py
