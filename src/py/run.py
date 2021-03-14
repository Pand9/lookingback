#!/usr/bin/env python3
import argparse
import logging
import os
import subprocess
from subprocess import PIPE

from easytrack.conf import Conf, load_conf
from easytrack.json import to_json
from easytrack.trackdir import Trackdir

log = logging.getLogger(__name__)


def open_trackdir(conf: Conf):
    trackdir = Trackdir(conf)
    subprocess.run(
        [
            "code",
            conf.track_dir,
            trackdir.state.statusfile_path(),
            *(f.path for f in trackdir.state.actives),
            os.path.expanduser("~/.config/easytrack/config.toml"),
        ],
        stdout=PIPE,
        stderr=PIPE,
        check=True,
    )


def prep_trackdir(conf: Conf):
    _ = Trackdir(conf)


def run_cli():
    conf = load_conf()

    parser = argparse.ArgumentParser(description="Run different easytrack components")
    parser.add_argument('-v', '--verbose', action='store_true')

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    trackdir_parser = subparsers.add_parser("trackdir")
    setup_trackdir_parser(trackdir_parser)

    _ = subparsers.add_parser("config")

    args = parser.parse_args()

    logging.basicConfig(level="INFO" if not args.verbose else "DEBUG")

    if args.cmd == "trackdir":
        if args.trackdir_cmd == "prep":
            prep_trackdir(conf)
        elif args.trackdir_cmd == "open":
            open_trackdir(conf)
    elif args.cmd == "config":
        print(to_json(conf))


def setup_trackdir_parser(parser):
    subparsers = parser.add_subparsers(dest="trackdir_cmd", required=True)
    subparsers.add_parser("prep")
    subparsers.add_parser("open")


if __name__ == "__main__":
    # import sys
    # sys.argv.extend(['trackdir', 'prep'])
    run_cli()
