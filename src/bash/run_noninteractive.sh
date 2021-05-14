#!/bin/bash

EASYTRACK_ALERT_METHOD=notify-send EASYTRACK_LOG_OUTPUT=file $(dirname $0)/run.sh "$@"