#!/bin/bash
# by vaz
# hide border_width when there is only 1 window
set -o verbose

while true;do
    status=$(pidof /home/vaz/USB/backup/code/vxma_web/runbot.sh)
    if [[ -f ${status} ]]; then
        echo "found"
        bash ~/USB/backup/code/vxma_web/runbot.sh
    fi
done
