import logging
from pathlib import Path

from easytrack.togglexport.alias_db import AliasDB
from easytrack.togglexport.calc_status import calc_status
from easytrack.togglexport.task_db import TaskDB
from easytrack.togglexport.toggl_add_entries import toggl_add_entries
from easytrack.togglexport.toggl_delete_entries import toggl_delete_entries_for_dates
from easytrack.togglexport.togglfile import parse_toggl_file

log = logging.getLogger(__name__)


def run_export(
    taskcachepath: Path,
    aliasespath: Path,
    statuspath: Path,
    togglpath: Path,
):
    tasks = TaskDB(taskcachepath).get_tasks()
    aliases = AliasDB(aliasespath).get_aliases()

    togglfile = parse_toggl_file(togglpath.read_text(), aliases)

    localentries = togglfile.entries
    dates = togglfile.get_dates()

    toggl_delete_entries_for_dates(dates)
    toggl_add_entries(localentries, tasks)

    calc_status(taskcachepath, aliasespath, statuspath, togglpath)
