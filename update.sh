#!/bin/bash

docker cp vxma_d/ vxmaBots:/
docker restart vxmaBots
