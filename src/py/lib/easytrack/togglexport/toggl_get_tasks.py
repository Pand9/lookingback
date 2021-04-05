import os
from dataclasses import dataclass
from typing import List

from toggl.TogglPy import Endpoints, Toggl


@dataclass
class TglTask:
    project_id: int
    project_name: str
    task_id: int
    task_name: str


def toggl_get_tasks(token=None) -> List[TglTask]:
    toggl = Toggl()
    if token is None:
        token = os.getenv("TOGGL_API_TOKEN")
    toggl.setAPIKey(token)

    workspaces = []
    for e in toggl.getWorkspaces():
        workspaces.append((e["id"], e["name"]))

    projects = []
    for wid, wname in workspaces:
        for e in toggl.request(Endpoints.WORKSPACES + f"/{wid}/projects") or []:
            projects.append((e["id"], e["name"]))

    ptasks = []
    for pid, pname in projects:
        for e in toggl.getProjectTasks(pid) or [{"id": 0, "name": ""}]:
            ptasks.append(TglTask(pid, pname, e["id"], e["name"]))

    return ptasks
