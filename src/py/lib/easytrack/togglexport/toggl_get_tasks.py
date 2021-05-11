import os
import logging
import time
from dataclasses import dataclass
from typing import List
import urllib

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
    for e in _retry(lambda: toggl.getWorkspaces()):
        workspaces.append((e["id"], e["name"]))

    projects = []
    for wid, wname in workspaces:
        for e in _retry(lambda: toggl.request(Endpoints.WORKSPACES + f"/{wid}/projects")) or []:
            projects.append((e["id"], e["name"]))

    ptasks = []
    for pid, pname in projects:
        for e in _retry(lambda: toggl.getProjectTasks(pid)) or [{"id": 0, "name": ""}]:
            ptasks.append(TglTask(pid, pname, e["id"], e["name"]))

    return ptasks


def _retry(func, max_retries=10, wait_seconds=0.1):
    retries = 0
    while True:
        try:
            res = func()
            if retries:
                logging.debug(f'Success on retry {retries}')
            return res
        except urllib.error.HTTPError:
            logging.debug("Repeating url request")
            retries += 1
            if retries == max_retries:
                raise
            else:
                time.sleep(wait_seconds)
