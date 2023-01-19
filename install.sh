#!/bin/bash

mv vxma.db vxma.dbo
cp ../vxma.db .
docker build -t vxma_web .
