#!/usr/bin/env python3
import argparse
import datetime
import json
import logging
import os
import shlex
import subprocess
import sys
from subprocess import PIPE

import dateutil.parser
from easytrack.conf import Conf, load_conf
from easytrack.jsonfmt import to_json
from easytrack.monitor import MonitorState
from easytrack.reporter import print_basic_format, transform_report
from easytrack.togglexport.calc_status import calc_status
from easytrack.togglexport.run_export import run_export
from easytrack.togglexport.task_db import TaskDB
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


def toggl_status(conf: Conf, local: bool = False):
    trackdir = Trackdir(conf).state
    calc_status(
        trackdir.toggl_taskcache_path(),
        trackdir.toggl_aliases_path(),
        trackdir.exportstatus_file(),
        trackdir.exporting_file(),
        local=local,
    )


def toggl_export(conf: Conf):
    trackdir = Trackdir(conf).state
    run_export(
        trackdir.toggl_taskcache_path(),
        trackdir.toggl_aliases_path(),
        trackdir.exportstatus_file(),
        trackdir.exporting_file(),
    )
    toggl_status(conf)


def toggl_download_tasks(conf: Conf):
    trackdir = Trackdir(conf).state
    TaskDB(trackdir.toggl_taskcache_path()).cache_refresh()


def reporter_report(conf: Conf, input_args):
    rust_bin = os.getenv("EASYTRACK_REDUCER_RUST_BIN_PATH")
    if rust_bin is None:
        raise ValueError("rust binary path was not provided")
    if not os.path.exists(rust_bin):
        raise ValueError(f"rust binary path not found at {rust_bin}")
    argv = [
        rust_bin,
        "--from",
        serialize_arg_fromto(input_args.from_),
        "--to",
        serialize_arg_fromto(input_args.to),
        "--chunk-minutes",
        str(input_args.chunk_minutes),
        "--chunk-colors",
        str(input_args.chunk_colors),
        "--format",
        "jsonstream",
        "--monitor-dir",
        str(conf.track_dir / "monitor"),
    ]
    log.info('running "%s"', shlex.join(argv))
    res = subprocess.run(argv, capture_output=True, text=True)
    if res.returncode != 0:
        log.error("rust stdout: %s", res.stdout)
        log.error("rust stderr: %s", res.stderr)
        res.check_returncode()
    if res.stderr:
        log.warning("rust stderr: %s", res.stderr)
    report = [json.loads(line) for line in res.stdout.split("\n") if line]
    report = transform_report(report, input_args.features)
    if input_args.output != "-":
        raise ValueError('Only output "-" supported for now')

    if input_args.format == "jsonpretty":
        print(json.dumps(report, indent=4))
    elif input_args.format == "jsonstream":
        for row in report:
            print(json.dumps(row))
    elif input_args.format == "basic":
        print_basic_format(report, sys.stdout)
    else:
        raise ValueError(f"Unsupported format {input_args.format}")


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
    setup_trackdir_parser(subparsers.add_parser("trackdir"))
    _ = subparsers.add_parser("config")
    _ = subparsers.add_parser("remind")
    setup_monitor_parser(subparsers.add_parser("monitor"))
    setup_toggl_parser(subparsers.add_parser("toggl"))
    setup_reporter_parser(subparsers.add_parser("reporter"))

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
    elif args.cmd == "toggl":
        if args.toggl_cmd == "download-tasks":
            toggl_download_tasks(conf)
        elif args.toggl_cmd == "status":
            toggl_status(conf, args.local)
        elif args.toggl_cmd == "export":
            toggl_export(conf)
    elif args.cmd == "reporter":
        if args.reporter_cmd == "report":
            reporter_report(conf, args)


def setup_trackdir_parser(parser):
    subparsers = parser.add_subparsers(dest="trackdir_cmd", required=True)
    _ = subparsers.add_parser("prep")
    _ = subparsers.add_parser("open")


def setup_monitor_parser(parser):
    parser.add_argument(
        "--ticks", default=60, type=int, help="how many monitor ticks per a process run"
    )


def setup_toggl_parser(parser):
    subparsers = parser.add_subparsers(dest="toggl_cmd", required=True)
    _ = subparsers.add_parser("download-tasks")
    validate = subparsers.add_parser("status")
    validate.add_argument("--local", action="store_true")
    _ = subparsers.add_parser("export")


def setup_reporter_parser(parser):
    subparsers = parser.add_subparsers(dest="reporter_cmd", required=True)
    report = subparsers.add_parser(
        "report", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    default_to = parse_arg_fromto(
        serialize_arg_fromto(datetime.datetime.now())
    ).replace(tzinfo=None)
    default_from = parse_arg_fromto(default_to.date().isoformat()).replace(tzinfo=None)
    report.add_argument(
        "--from",
        type=parse_arg_fromto,
        dest="from_",
        default=default_from,
        help="left bound",
    )
    report.add_argument(
        "--to", type=parse_arg_fromto, default=default_to, help="right bound"
    )
    report.add_argument(
        "--chunk-minutes", type=int, default=0, help="minutes per a single aggregate"
    )
    report.add_argument(
        "--chunk-colors",
        type=int,
        default=0,
        help="top x categories in a single aggregate",
    )
    report.add_argument(
        "--format",
        default="basic",
        help="output format, basic jsonstream or jsonpretty",
    )
    report.add_argument("--features", nargs="*", help="enable various report features")
    report.add_argument(
        "--output", default="-", help='supported are "-" (default) and "workspace"'
    )


def parse_arg_fromto(arg):
    return dateutil.parser.parse(arg).astimezone()


def serialize_arg_fromto(arg: datetime.datetime) -> str:
    return arg.astimezone().strftime("%Y-%m-%dT%H:%M")


if __name__ == "__main__":
    # import sys
    # sys.argv.extend(['trackdir', 'prep'])
    run_cli()
