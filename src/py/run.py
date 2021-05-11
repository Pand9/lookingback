#!/usr/bin/env python3

import argparse
import datetime
import errno
import fcntl
import json
import logging
import os
import shlex
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from subprocess import PIPE
from typing import List, Tuple

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


def ensure_rust_bin() -> Tuple[List[str], str]:
    """Returns command prefix to run (cargo run ... --) and CWD path, based on env variables"""
    rust_bin_value = os.getenv("EASYTRACK_RUST_REDUCER_BIN_PATH")
    if rust_bin_value is None:
        rust_src = os.getenv("EASYTRACK_RUST_SOURCE_PATH")
        if rust_src is None:
            bin_var = "EASYTRACK_RUST_REDUCER_BIN_PATH"
            src_var = "EASYTRACK_RUST_SOURCE_PATH"
            raise ValueError(f"neither {bin_var}, nor {src_var} provided")
        cargo_run_args = shlex.split(os.getenv("EASYTRACK_RUST_CARGO_RUN_ARGS") or "")
        return ["cargo", "run", *cargo_run_args, "--"], rust_src
    else:
        if not os.path.exists(rust_bin_value):
            raise ValueError(f"rust binary path not found at {rust_bin_value}")
        return [rust_bin_value], "."


def reporter_report(conf: Conf, input_args):
    rust_bin, cwd = ensure_rust_bin()
    argv = [
        *rust_bin,
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
    log.info('running "%s" in "%s"', shlex.join(argv), cwd)
    res = subprocess.run(argv, capture_output=True, text=True, cwd=cwd)
    if res.returncode != 0:
        log.error("rust stdout: %s", res.stdout)
        log.error("rust stderr: %s", res.stderr)
        res.check_returncode()
    if res.stderr:
        log.warning("rust stderr: %s", res.stderr)
    return _handle_report(input_args, res.stdout)


def _handle_report(input_args, report_data: str):
    report = [json.loads(line) for line in report_data.split("\n") if line]
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
    duration_minutes = duration.seconds // 60
    msg = f"Elapsed {duration_minutes} minutes since last time entry"
    alert_method = os.getenv("EASYTRACK_ALERT_METHOD")
    if alert_method == "notify-send":
        cmd = ["notify-send"]
        if critical:
            cmd += ["--urgency=critical"]
        cmd += ["--app-name=easytrack", "Remember to track time", msg]
        log.info('running "%s"', shlex.join(cmd))
        subprocess.run(cmd, stdout=PIPE, stderr=PIPE, check=True)
    elif alert_method == os.getenv("EASYTRACK_ALERT_METHOD") == "stdout":
        print(
            json.dumps(
                {
                    "type": "alert",
                    "msg": msg,
                    "duration_minutes": duration_minutes,
                    **({"is_critical": True} if critical else {}),
                }
            )
        )
    else:
        raise ValueError(f'unknown EASYTRACK_ALERT_METHOD value {alert_method}')


@contextmanager
def spinlock(lock_path: Path):
    lock_file = lock_path.open("w")
    while True:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError as e:
            if e.errno == errno.EAGAIN:
                print("file locked; trying again in 1s", file=sys.stderr)
                time.sleep(1)
            else:
                raise
    yield
    fcntl.flock(lock_file, fcntl.LOCK_UN)
    lock_file.close()


@contextmanager
def workdir_setup(conf: Conf, input_args):
    cmd = input_args.cmd
    if cmd == "config":
        yield
        return
    elif cmd in ("trackdir", "remind"):
        workdir_name = "trackdir"
    else:
        workdir_name = cmd

    try:
        workdir_path = conf.track_dir / "workdir" / workdir_name
        workdir_path.mkdir(parents=True, exist_ok=True)
        with spinlock(workdir_path / "lock"):
            logging_setup(input_args, workdir_path)
            yield
    except OSError as e:
        raise Exception(f"Locking error for {workdir_path}") from e


def logging_setup(input_args, workdir_path: Path):
    log_level = "INFO" if not input_args.verbose else "DEBUG"
    log_variant = os.getenv("EASYTRACK_LOG_OUTPUT")
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d|%(levelname).1s|%(lineno)3d| %(message)s",
        datefmt="%F_%T",
        level=log_level,
    )
    if log_variant == "file":
        filename = workdir_path / f"{datetime.date.today()}.reporter.log"
        handler = logging.FileHandler(str(filename))
        handler.setLevel('INFO')
        logging.getLogger().addHandler(handler)

    logging.info(f'Running "{shlex.join(sys.argv)}"')


def run_cli():
    conf = load_conf()

    parser = setup_common(
        argparse.ArgumentParser(description="Run different easytrack components")
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    setup_trackdir_parser(subparsers.add_parser("trackdir"))
    setup_common(subparsers.add_parser("config"))
    setup_common(subparsers.add_parser("remind"))
    setup_monitor_parser(subparsers.add_parser("monitor"))
    setup_toggl_parser(subparsers.add_parser("toggl"))
    setup_reporter_parser(subparsers.add_parser("reporter"))

    args = parser.parse_args()

    with workdir_setup(conf, args):
        if args.cmd == "trackdir":
            if args.trackdir_cmd == "prep":
                common_routine(conf)
                logging.info('Finished prepping the trackdir')
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
    setup_common(parser)
    subparsers = parser.add_subparsers(dest="trackdir_cmd", required=True)
    _ = setup_common(subparsers.add_parser("prep"))
    _ = setup_common(subparsers.add_parser("open"))


def setup_monitor_parser(parser):
    setup_common(parser)
    parser.add_argument(
        "--ticks", default=60, type=int, help="how many monitor ticks per a process run"
    )


def setup_toggl_parser(parser):
    setup_common(parser)
    subparsers = parser.add_subparsers(dest="toggl_cmd", required=True)
    _ = subparsers.add_parser("download-tasks")
    validate = setup_common(subparsers.add_parser("status"))
    validate.add_argument("--local", action="store_true")
    _ = subparsers.add_parser("export")


def setup_reporter_parser(parser):
    setup_common(parser)
    subparsers = parser.add_subparsers(dest="reporter_cmd", required=True)
    report = setup_common(
        subparsers.add_parser(
            "report", formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
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


def setup_common(parser):
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="print useful troubleshooting info"
    )
    return parser


if __name__ == "__main__":
    # import sys
    # sys.argv.extend(['trackdir', 'prep'])
    run_cli()
