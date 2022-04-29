#!/usr/bin/env bash

# 1. Create a dir `customer` in the same dir as `te-canvas` and `te-canvas-front`
# 2. cd into `customer` and execute `../te-canvas/symlink.sh`
# 3. Add symlinks ssl.crt, ssl.key pointing to cert keypair
# 4. docker-compose -f front.yml -f back.yml --profile api --profile sync up -d

ln -s ../te-canvas/docker-compose.yml back.yml
ln -s ../te-canvas-front/docker-compose.yml front.yml
ln -s ../te-canvas-front/nginx-docker.conf .
