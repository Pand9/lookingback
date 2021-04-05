#!/bin/bash

if [[ $EASYTRACK_PYTHON_VENV_ACTIVATE ]]; then
    source "$EASYTRACK_PYTHON_VENV_ACTIVATE"
fi

export PYTHONPATH="$PYTHONPATH:$(dirname $0)/../py/lib"

track_dir=$(python3 "$(dirname $0)/../py/run.py" config | jq -r .track_dir)
if [[ -z ${track_dir} ]]; then exit 1; fi
track_dir="${track_dir//\~/$HOME}"
mkdir -p "$track_dir"

err="$track_dir/monitor_run.err"
lock="$track_dir/monitor_run.lock"

echo "$(date -Iseconds)| running $0 $@" >> "$err"
(
    flock --wait 5 --verbose 9 1>> "$err" || exit 1
    python3 "$(dirname $0)/../py/run.py" monitor $@ |& tee --append "$err"
) 9> "$lock"