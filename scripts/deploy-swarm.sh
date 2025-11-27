#!/usr/bin/env bash
set -e
STACK_NAME="timetable-scd"
docker stack deploy -c stack-scd.yml $STACK_NAME
