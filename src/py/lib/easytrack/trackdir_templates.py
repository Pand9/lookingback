TASKS_JSON_TEXT = """{
    // See https://go.microsoft.com/fwlink/?LinkId=733558
    // for the documentation about the tasks.json format
    "version": "2.0.0",
    "tasks": [
        {
            "label": "toggl download tasks",
            "type": "shell",
            "command": "$EASYTRACK_BASH_SOURCE_PATH/run.sh toggl download-tasks"
        },
        {
            "label": "toggl validate (local)",
            "type": "shell",
            "command": "$EASYTRACK_BASH_SOURCE_PATH/run.sh toggl status --local"
        },
        {
            "label": "toggl validate",
            "type": "shell",
            "command": "$EASYTRACK_BASH_SOURCE_PATH/run.sh toggl status"
        },
        {
            "label": "toggl export",
            "type": "shell",
            "command": "$EASYTRACK_BASH_SOURCE_PATH/run.sh toggl export"
        },
    ]
}"""

RUN_SH_TEXT = """#!/bin/bash
EASYTRACK_TRACK_DIR=$(dirname $(dirname $0)) /home/ks/personal/easyinsert/src/bash/run.sh $@
"""

RUN_NONINTERACTIVE_SH_TEXT = """#!/bin/bash
EASYTRACK_TRACK_DIR=$(dirname $(dirname $0)) /home/ks/personal/easyinsert/src/bash/run_noninteractive.sh $@
"""
