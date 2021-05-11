#!/bin/bash

EASYTRACK_ALERT_METHOD=notify-send EASYTRACK_LOG_OUTPUT=workspace $(dirname $0)/run.sh "$@"