import os
import urllib.error
from typing import List

from easytrack.togglexport.entry import TglStandardEntry
from easytrack.togglexport.toggl_get_tasks import TglTask
from toggl.TogglPy import Endpoints, Toggl


class ConvertingError(Exception):
    def __init__(self, msg, i=None, line=None):
        self.i = i
        self.line = line
        super().__init__(msg)

    def __str__(self):
        return f"{super().__str__()}; line number: {self.i}; line: {self.line}"


class TogglError(Exception):
    def __init__(self, body=None, underlying=None):
        self.body = body
        self.underlying = underlying

    def __str__(self):
        return f"{super().__str__()}; underlying: {self.underlying}; body: {self.body}"


def toggl_add_entries(
    entries: List[TglStandardEntry], tasks: List[TglTask], token=None
):
    toggl = Toggl()
    if token is None:
        token = os.getenv("TOGGL_API_TOKEN")
    toggl.setAPIKey(token)

    taskmap = {}
    for t in tasks:
        k = t.project_name, t.task_name
        v = t.project_id, t.task_id
        taskmap[k] = v

    togglentries = []
    for i, entry in enumerate(entries, start=1):
        try:
            try:
                pid, tid = taskmap[(entry.project, entry.task)]
            except KeyError:
                raise ConvertingError(f"{entry.project}, {entry.task} not found")
            togglentry = {
                "description": entry.description,
                "pid": pid,
                "tid": tid if tid else None,
                "start": entry.start.astimezone().isoformat(),
                "duration": entry.duration.seconds,
                "created_with": "easytrack",
            }
            togglentries.append(togglentry)
        except ConvertingError as e:
            e.i = i
            e.line = e
            raise

    for i, togglentry in enumerate(togglentries, start=1):
        try:
            try:
                resp = toggl.postRequest(
                    Endpoints.TIME_ENTRIES, {"time_entry": togglentry}
                )
            except urllib.error.HTTPError as e:
                raise TogglError(body=e.fp.read().decode(), underlying=e)
            resp = toggl.decodeJSON(resp)
            if resp.get("data") is None:
                raise ConvertingError(f"data not found in resp {resp}")
        except ConvertingError as e:
            e.i = i
            e.line = e
            raise

    # te = togglrequest['time_entry'][0]
    # toggl.createTimeEntry(3, 'desc', year=2021, month=4, day=5, taskid=te['tid'], projectid=te['pid'])


if __name__ == "__main__":
    content = """
2021-04-05
11:00 5h 15m | [dev] asd
20m | [dev] ddf
2021-04-04
3h | ddf [planning]
    """
    from easytrack.togglexport.alias_db import AliasDB
    from easytrack.togglexport.task_db import TaskDB
    from easytrack.togglexport.togglfile import parse_toggl_file

    tasks = TaskDB("/home/ks/workdir/trackdir/toggl_task_cache.json").get_tasks()
    aliases = AliasDB("/home/ks/workdir/trackdir/toggl_aliases.json").get_aliases()

    entries = parse_toggl_file(content, aliases).entries
    toggl_add_entries(entries, tasks)
