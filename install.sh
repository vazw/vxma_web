#!/bin/bash

docker kill vxmaBots
docker container prune
docker build -t vxma_web .
docker run -p 8050:8050 --name vxmaBots -d vxma_web
