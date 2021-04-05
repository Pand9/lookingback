import datetime
import os
from typing import List

from easytrack.togglexport.toggl_get_entries import toggl_get_entries_raw
from toggl.TogglPy import Endpoints, Toggl


class TogglError(Exception):
    def __init__(self, body=None, underlying=None):
        self.body = body
        self.underlying = underlying

    def __str__(self):
        return f"{super().__str__()}; underlying: {self.underlying}; body: {self.body}"


def toggl_delete_entries_for_dates(dates: List[datetime.date], token=None) -> None:
    ids = set()
    for date in dates:
        togglentries = toggl_get_entries_raw(date, token)
        for togglentry in togglentries:
            ids.add(togglentry["id"])
    return toggl_delete_entries_for_ids(ids, token)


def toggl_delete_entries_for_ids(ids, token=None):
    toggl = Toggl()
    if token is None:
        token = os.getenv("TOGGL_API_TOKEN")
    toggl.setAPIKey(token)

    for id_ in ids:
        endpoint = Endpoints.TIME_ENTRIES + f"/{id_}"
        toggl_http_request(toggl, endpoint, "DELETE")


def toggl_http_request(toggl, endpoint, method):
    from urllib.request import Request, urlopen

    req = Request(endpoint, headers=toggl.headers, method=method)
    resp = urlopen(req).read()
    return resp


if __name__ == "__main__":
    toggl_delete_entries_for_dates([datetime.date(2021, 4, 5)])
