#!/usr/bin/env bash

docker-compose --profile test up -d
python -m unittest discover -s te_canvas/test -f $@