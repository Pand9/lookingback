#!/usr/bin/env python3

import argparse
import datetime
import errno
import fcntl
import inspect
import json
import logging
import os
import shlex
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import List, Tuple

import dateutil.parser
from easytrack.conf import Conf, load_conf
from easytrack.jsonfmt import to_json
from easytrack.monitor import MonitorState
from easytrack.reporter import print_basic_format, transform_report
from easytrack.time import now
from easytrack.vacuum import do_vacuum

log = logging.getLogger(__name__)


def ensure_rust_bin() -> Tuple[List[str], str]:
    """Returns command prefix to run (cargo run ... --) and CWD path, based on env variables"""
    rust_bin_value = os.getenv("EASYTRACK_RUST_REDUCER_BIN_PATH")
    if rust_bin_value is None:
        rust_src = os.getenv("EASYTRACK_RUST_SOURCE_PATH")
        if rust_src is None:
            rust_src = f"{os.path.dirname(inspect.getfile(inspect.currentframe()))}/../rust"
        cargo_run_args = shlex.split(os.getenv("EASYTRACK_RUST_CARGO_RUN_ARGS", "--release"))
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
        mk_str_fromto(input_args.from_),
        "--to",
        mk_str_fromto(input_args.to),
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


class FlockError(Exception):
    pass


@contextmanager
def do_lock(lock_path: Path):
    try:
        lock_file = lock_path.open("w")
        while True:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    print(lock_path, "locked; trying again in 0.1s", file=sys.stderr)
                    time.sleep(0.1)
                else:
                    raise FlockError(f"Locking error for {lock_path}") from e
        yield
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)


@contextmanager
def cmddir_lock(conf: Conf, input_args):
    workdir_path = conf.track_dir / input_args.cmd
    workdir_path.mkdir(parents=True, exist_ok=True)
    with do_lock(workdir_path / "lock"):
        yield workdir_path


def run_cli():
    conf = load_conf()

    parser = setup_common(argparse.ArgumentParser(description="Run different easytrack components"))
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    setup_common(subparsers.add_parser("config"))
    setup_monitor_parser(subparsers.add_parser("monitor"))
    setup_report_parser(subparsers.add_parser("report"))
    setup_vacuum_parser(subparsers.add_parser("vacuum", help="clean old data"))

    args = parser.parse_args()

    with cmddir_lock(conf, args) as cmddir_path:
        _init_log(cmddir_path, verbose=args.verbose)
        if args.cmd == "config":
            print(to_json(conf))
        elif args.cmd == "monitor":
            _run_monitor(conf, args.ticks)
        elif args.cmd == "report":
            reporter_report(conf, args)
        elif args.cmd == "vacuum":
            do_vacuum(
                conf,
                verb=args.verb,
                desc=args.desc,
                advs=args.advs,
                dry_run=args.dry_run,
            )


def _init_log(cmddir_path, verbose: bool):
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d|%(levelname).1s|%(lineno)3d| %(message)s",
        datefmt="%F_%T",
        level="INFO" if not verbose else "DEBUG",
    )
    file_handler = logging.FileHandler(str(cmddir_path / f"{datetime.date.today()}.log"))
    file_handler.setLevel("INFO")
    logging.getLogger().addHandler(file_handler)


def setup_monitor_parser(parser):
    setup_common(parser)
    parser.add_argument("--ticks", default=60, type=int, help="how many monitor ticks per a process run")


def setup_report_parser(parser):
    setup_common(parser)
    default_to = parse_arg_fromto(mk_str_fromto(now())).replace(tzinfo=None)
    default_from = parse_arg_fromto(default_to.date().isoformat()).replace(tzinfo=None)
    parser.add_argument(
        "--from",
        type=parse_arg_fromto,
        dest="from_",
        default=default_from,
        help="left bound",
    )
    parser.add_argument("--to", type=parse_arg_fromto, default=default_to, help="right bound")
    parser.add_argument("--chunk-minutes", type=int, default=0, help="minutes per a single aggregate")
    parser.add_argument(
        "--chunk-colors",
        type=int,
        default=0,
        help="top x categories in a single aggregate",
    )
    parser.add_argument(
        "--format",
        default="basic",
        help="output format, basic jsonstream or jsonpretty",
    )
    parser.add_argument("--features", nargs="*", help="enable various report features")
    parser.add_argument("--output", default="-", help='supported are "-" (default) and "workspace"')


def setup_vacuum_parser(vacuum):
    setup_common(vacuum)
    vacuum.add_argument("verb", choices=["delete", "archive"])
    vacuum.add_argument("desc", choices=["all", "old"])
    vacuum.add_argument("advs", nargs="*", choices=["monits", "logs"])
    vacuum.add_argument("--dry-run", action="store_true")


def parse_arg_fromto(arg):
    return dateutil.parser.parse(arg).astimezone()


def mk_str_fromto(arg: datetime.datetime) -> str:
    return arg.astimezone().strftime("%Y-%m-%dT%H:%M")


def setup_common(parser):
    parser.add_argument("-v", "--verbose", action="store_true", help="print useful troubleshooting info")
    return parser


if __name__ == "__main__":
    run_cli()
