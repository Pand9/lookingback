import datetime
import logging
from pathlib import Path

from easytrack.togglexport.alias_db import AliasDB
from easytrack.togglexport.task_db import TaskDB
from easytrack.togglexport.toggl_get_entries import toggl_get_entries
from easytrack.togglexport.togglfile import parse_toggl_file

log = logging.getLogger(__name__)


def calc_status(
    taskcachepath: Path,
    aliasespath: Path,
    statuspath: Path,
    togglpath: Path,
    local: bool = False
):
    tasks = TaskDB(taskcachepath).get_tasks()
    aliases = AliasDB(aliasespath).get_aliases()
    with statuspath.open("w") as statusfile:
        if not tasks:
            print('There are no task definitions. Please run "toggl download-tasks"', file=statusfile)
        if not aliases:
            print(f'There are no aliases. Please open {aliasespath} and define some aliases.', file=statusfile)
        if not tasks or not aliases:
            return

    togglfile = parse_toggl_file(togglpath.read_text(), aliases)

    if not local:
        systementries = toggl_get_entries(togglfile.dates(), tasks, aliases)
    else:
        systementries = None
    localentries = togglfile.entries
    _do_report(systementries, localentries, statusfile)


def _do_report(systementries, localentries, statusfile):
    def _print(*a, **kw):
        print(*a, **kw, file=statusfile)

    curtime = datetime.datetime.now().time()

    _print("# Easytrack export report")
    _print()
    _print("Generated:", curtime.isoformat(timespec="seconds"))

    if localentries is not None:
        _print()
        _print("## Local entries")
        _print()

        for entry in localentries:
            _print(entry)

    if systementries is not None:
        _print()
        _print("## System entries")
        _print()

        for entry in systementries:
            _print(entry)
