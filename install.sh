#!/bin/bash

docker kill vxmaBots
docker container prune
docker build -t vxma_web .
