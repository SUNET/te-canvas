#!/usr/bin/env bash

pydoc -w \
te_canvas \
te_canvas.api \
te_canvas.api_ns.canvas \
te_canvas.api_ns.config \
te_canvas.api_ns.connection \
te_canvas.api_ns.timeedit \
te_canvas.api_ns.version \
te_canvas.canvas \
te_canvas.db \
te_canvas.log \
te_canvas.scripts.clear_events \
te_canvas.scripts.parallel_test \
te_canvas.sync \
te_canvas.test \
te_canvas.test.common \
te_canvas.test.test_api \
te_canvas.test.test_canvas \
te_canvas.test.test_db \
te_canvas.test.test_sync \
te_canvas.test.test_timeedit \
te_canvas.test.test_translator \
te_canvas.timeedit \
te_canvas.translator \
te_canvas.util

mkdir -p docs
mv te_canvas*.html docs
