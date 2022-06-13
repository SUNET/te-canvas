#!/usr/bin/env bash

docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile sync --profile api up -d --build
