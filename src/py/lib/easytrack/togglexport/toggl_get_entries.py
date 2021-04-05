from typing import List
import datetime
import os
from easytrack.togglexport.entry import TglStandardEntry
from easytrack.togglexport.alias_db import Alias
from easytrack.togglexport.toggl_get_tasks import TglTask
from toggl.TogglPy import Toggl, Endpoints


class MappingError(Exception):
    def __init__(self, msg, i=None, line=None):
        self.i = i
        self.line = line
        super().__init__(msg)

    def __str__(self):
        return f"{super().__str__()}; line number: {self.i}; line: {self.line}"


def toggl_get_entries(
    date: datetime.date, tasks: List[TglTask], aliases: List[Alias], token=None
) -> List[TglStandardEntry]:
    togglentries = toggl_get_entries_raw(date, token)
    return parse_entries(togglentries, tasks, aliases)


def toggl_get_entries_raw(date: datetime.date, token=None):
    toggl = Toggl()
    if token is None:
        token = os.getenv("TOGGL_API_TOKEN")
    toggl.setAPIKey(token)

    start_date = datetime.datetime.combine(date, datetime.time()).astimezone()
    params = {"start_date": start_date.isoformat()}
    params["end_date"] = (
        start_date + datetime.timedelta(days=1) + datetime.timedelta(minutes=-1)
    ).isoformat()

    togglentries = toggl.request(Endpoints.TIME_ENTRIES, params)
    return togglentries


def parse_entries(togglentries, tasks: List[TglTask], aliases: List[Alias]):
    aliasmap = {}
    for a in aliases:
        k = a.project, a.task
        aliasmap[k] = a
    taskmap = {}
    for t in tasks:
        k = t.project_id, t.task_id
        v = t.project_name, t.task_name
        taskmap[k] = aliasmap.get(v)
        if taskmap[k] is None:
            taskmap[k] = Alias(
                alias=" - ".join(v), project=t.project_name, task=t.task_name
            )

    resrows = []

    for i, e in enumerate(togglentries, start=1):
        try:
            k = (e["pid"], e["tid"])
            alias = taskmap.get(k)
            if alias is None:
                raise MappingError(f"Task {k} not found in the local database")

            start = datetime.datetime.fromisoformat(e["start"])
            duration = datetime.timedelta(seconds=e["duration"])
            desc = e["description"]

            res = TglStandardEntry(
                start=start.astimezone().replace(tzinfo=None),
                duration=duration,
                ptask_alias=alias.aliases()[0],
                project=alias.project,
                task=alias.task,
                description=desc,
            )
            resrows.append(res)

        except MappingError as e:
            e.i = i
            e.line = e
            raise
    return resrows


if __name__ == "__main__":
    from easytrack.togglexport.alias_db import AliasDB
    from easytrack.togglexport.task_db import TaskDB

    aliases = AliasDB("/home/ks/workdir/trackdir/toggl_aliases.json").get_aliases()
    tasks = TaskDB("/home/ks/workdir/trackdir/toggl_task_cache.json").get_tasks()
    d = datetime.date(2021, 4, 4)
    res = toggl_get_entries(d, tasks, aliases)
    for r in res:
        print(r)
