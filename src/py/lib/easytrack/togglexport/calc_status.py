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
    local: bool = False,
):
    tasks = TaskDB(taskcachepath).get_tasks()
    aliases = AliasDB(aliasespath).get_aliases()
    with statuspath.open("w") as statusfile:
        if not tasks:
            print(
                'There are no task definitions. Please run "toggl download-tasks"',
                file=statusfile,
            )
        if not aliases:
            print(
                f"There are no aliases. Please open {aliasespath} and define some aliases.",
                file=statusfile,
            )
        if not tasks or not aliases:
            return

        togglfile = parse_toggl_file(togglpath.read_text(), aliases)

        if not local:
            systementries = toggl_get_entries(togglfile.get_dates(), tasks, aliases)
        else:
            systementries = None
        localentries = togglfile.entries
        _do_report(systementries, localentries, statusfile)


def _do_report(systementries, localentries, statusfile):
    if systementries is not None:
        systementries = sorted(e.normalize() for e in systementries)
    if localentries is not None:
        localentries = sorted(e.normalize() for e in localentries)
    if systementries is not None and localentries is not None:
        systementries = {e.normalize() for e in systementries}
        localentries = {e.normalize() for e in localentries}
        commones = systementries & localentries
        onlysystem = sorted(systementries - commones)
        onlylocal = sorted(localentries - commones)
        commones = sorted(commones)
    else:
        commones = []
        onlysystem = systementries
        onlylocal = localentries

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

        if onlylocal:
            for entry in onlylocal:
                _print(entry)
        else:
            _print("No such entries")

    if systementries is not None:
        _print()
        _print("## System entries")
        _print()

        if onlysystem:
            for entry in onlysystem:
                _print(entry)
        else:
            _print("No such entries")

    if systementries is not None and localentries is not None:
        _print()
        _print("## Identical system & local entries")
        _print()

        if commones:
            for entry in commones:
                _print(entry)
        else:
            _print("No such entries")
