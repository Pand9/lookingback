#!/bin/bash

runargs=("$@")

HELP_PREFIX=$(cat <<-END
## This is the help prefix - detailed cli help is at the bottom
## Input environment variables
# - $EASYTRACK_ALERT_METHOD - if "stdout" (default), alerts are not sent other than stdout; suitable for CLI. if "notify-send" provided, notify-send alerts are issued.
# - $EASYTRACK_PYTHON_VENV_ACTIVATE - python venv (optional, system python3 used otherwise)
# - $EASYTRACK_PY_SOURCE_PATH - defaults to $(dirname $0)/../py
# - $EASYTRACK_RUST_SOURCE_PATH - used only when EASYTRACK_RUST_REDUCER_BIN_PATH not provided. Defaults to $(dirname $0)/../rust
# - $EASYTRACK_RUST_REDUCER_BIN_PATH - If not provided, rust binary is ran with cargo build --release in $EASYTRACK_RUST_SOURCE_PATH
## Config file - ~/.config/easytrack/config.toml - has track_dir, softlimit, hardlimit
## External code/tool dependencies (for bash script wrapper only)
# - bash (/bin/bash) (tested on bash 5.0)
# - flock (tested on flock from util-linux 2.34)
# - gnu coreutils (e.g. date, dirname, tee) (tested on coreutils 8.30)
# - notify-send for notifications (tested on 0.7.9)
## Usage notes
# - Don't source, as script depends on $0 by default (see list of environment variables above).
## Error reporting & logs
# - All exceptions are reported with notify-send
# - $track_dir/(track.log|monitor.log|reporter.log) contain log entries - if they could be opened successfully of course. They are automatically rotated.
## Synchronization
# - Tracking, monitor & reporter each have their own exclusive lock. Two of each of those processes cannot run in parallel.
# - Locked file is $track_dir/(track.lock|monitor.lock|reporter.lock)
#
## This is end of the help prefix - detailed cli help is below
END
)

is_help() {
    local p
    for p in "${runargs[@]}"; do
        if [[ $p == -h || $p == --help ]]; then
            return 0
        fi
    done
    return 1
}

is_verbose() {
    local p
    for p in "${runargs[@]}"; do
        if [[ $p == -v || $p == --verbose ]]; then
            return 0
        fi
    done
    return 1
}

alert() {
    # >&2 echo "alert: $1; $2"
    if [[ "$EASYTRACK_ALERT_METHOD" = "notify-send" ]]; then
        notify-send --app-name=easytrack "$@"
    fi
}

if is_help; then echo "$HELP_PREFIX"; fi

variables=(EASYTRACK_ALERT_METHOD EASYTRACK_PYTHON_VENV_ACTIVATE EASYTRACK_PY_SOURCE_PATH EASYTRACK_RUST_SOURCE_PATH EASYTRACK_RUST_REDUCER_BIN_PATH EASYTRACK_RUST_CARGO_RUN_ARGS EASYTRACK_TRACK_DIR)

print_variables () {
    local p
    for p in ${variables[@]}; do
        >&2 echo "$p = ${!p}"
    done
}

if is_verbose; then >&2 echo "Verbose output enabled"; fi
if is_verbose; then >&2 echo "Input environment variables:"; print_variables; fi

export EASYTRACK_ALERT_METHOD=${EASYTRACK_ALERT_METHOD:-stdout}
if [[ "$EASYTRACK_ALERT_METHOD" != stdout && "$EASYTRACK_ALERT_METHOD" != notify-send ]]; then
    >&2 echo "run.sh error - unknown alert method $EASYTRACK_ALERT_METHOD. Supported: notify-send & stdout"
    exit 1
fi
EASYTRACK_PY_SOURCE_PATH=${EASYTRACK_PY_SOURCE_PATH:-$(dirname $0)/../py}

if is_verbose; then >&2 echo "Recalculated environment variables:"; print_variables; fi

if [[ $EASYTRACK_PYTHON_VENV_ACTIVATE ]]; then
    if is_verbose; then >&2 echo "Activating python3 venv"; fi
    source "$EASYTRACK_PYTHON_VENV_ACTIVATE"
else
    if is_verbose; then >&2 echo "Using system python3"; fi
fi

export PYTHONPATH="$PYTHONPATH:$EASYTRACK_PY_SOURCE_PATH/lib"
if is_verbose; then >&2 echo "updated PYTHONPATH: $PYTHONPATH"; fi

python3 "$EASYTRACK_PY_SOURCE_PATH/run.py" $@
code=$?
if is_verbose; then >&2 echo "python return code: $code"; fi
if [[ $code != 0 && $code != 42 ]]; then
    alert "easytrack error code $code" "see logs or run from shell: \"$0 $@\""
fi
