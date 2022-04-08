#!/usr/bin/env bash

# 1. Create a dir `customer` in the same dir as `te-canvas` and `te-canvas-front`
# 2. cd into `customer` and execute `../te-canvas/symlink.sh`

ln -s ../te-canvas/docker-compose.yml back.yml
ln -s ../te-canvas-front/docker-compose.yml front.yml
ln -s ../te-canvas-front/ssl.crt .
ln -s ../te-canvas-front/ssl.key .
ln -s ../te-canvas-front/nginx-docker.conf .
