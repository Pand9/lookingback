#!/usr/bin/env python3
import argparse
import logging
import os
import subprocess
from subprocess import PIPE

from easytrack.conf import Conf, load_conf
from easytrack.jsonfmt import to_json
from easytrack.monitor import MonitorState
from easytrack.trackdir import Trackdir

log = logging.getLogger(__name__)


def open_trackdir(conf: Conf):
    trackdir = common_routine(conf)
    subprocess.run(
        [
            "code",
            conf.track_dir,
            *(f.path for f in trackdir.state.actives),
            trackdir.state.statusfile_path(),
            os.path.expanduser("~/.config/easytrack/config.toml"),
        ],
        stdout=PIPE,
        stderr=PIPE,
        check=True,
    )


def common_routine(conf: Conf):
    trackdir = Trackdir(conf)
    actives = trackdir.state.actives
    if actives:
        duration = actives[0].duration_from_lasttime()
        if duration is not None:
            if duration.seconds // 60 >= conf.hardlimit:
                _send_reminder(duration, critical=True)
            elif duration.seconds // 60 >= conf.softlimit:
                _send_reminder(duration, critical=False)
    return trackdir


def _run_monitor(conf: Conf, ticks: int):
    monitor_state = MonitorState(
        ticks=ticks,
        output_filename_rotate_frequency_minutes=5,
        output_dir=conf.track_dir / "monitor",
    )
    monitor_state.run_monitor()


def _send_reminder(duration, critical=False):
    cmd = ["notify-send"]
    if critical:
        cmd += ["--urgency=critical"]
    cmd += ["--app-name=easytrack", "Remember to track time"]
    cmd += [f"Elapsed {duration.seconds // 60} minutes since last time entry"]
    subprocess.run(cmd, stdout=PIPE, stderr=PIPE, check=True)


def run_cli():
    conf = load_conf()

    parser = argparse.ArgumentParser(description="Run different easytrack components")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    trackdir_parser = subparsers.add_parser("trackdir")
    setup_trackdir_parser(trackdir_parser)

    _ = subparsers.add_parser("config")
    _ = subparsers.add_parser("remind")

    monitor_parser = subparsers.add_parser("monitor")
    setup_monitor_parser(monitor_parser)

    args = parser.parse_args()

    logging.basicConfig(level="INFO" if not args.verbose else "DEBUG")

    if args.cmd == "trackdir":
        if args.trackdir_cmd == "prep":
            common_routine(conf)
        elif args.trackdir_cmd == "open":
            open_trackdir(conf)
    elif args.cmd == "config":
        print(to_json(conf))
    elif args.cmd == "remind":
        common_routine(conf)
    elif args.cmd == "monitor":
        _run_monitor(conf, args.ticks)


def setup_trackdir_parser(parser):
    subparsers = parser.add_subparsers(dest="trackdir_cmd", required=True)
    _ = subparsers.add_parser("prep")
    _ = subparsers.add_parser("open")


def setup_monitor_parser(parser):
    parser.add_argument(
        "--ticks", default=60, type=int, help="how many monitor ticks per a process run"
    )


if __name__ == "__main__":
    # import sys
    # sys.argv.extend(['trackdir', 'prep'])
    run_cli()
