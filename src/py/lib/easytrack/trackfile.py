import datetime
from dataclasses import dataclass
from functools import lru_cache
import re
import os
from pathlib import Path
from easytrack.time import duration, now
import logging
log = logging.getLogger(__name__)


# Explore it at: https://regex101.com/
TIME_RE_TXT = r"\s*((?P<first_time>[0-9][0-9](:[0-9][0-9])?)\s*-\s*)?(?P<last_time>[0-9][0-9](:[0-9][0-9])?).*"


@dataclass(eq=True)
class TrackfileState:
    path: Path
    day: datetime.date
    active_lasttime: datetime.time
    finished: bool
    exported: bool

    def last_datetime(self) -> datetime.datetime:
        if self.active_lasttime is None:
            return None
        return datetime.datetime.combine(self.day, self.active_lasttime)

    def duration_from_lasttime(self) -> datetime.timedelta:
        if self.active_lasttime is None:
            return None
        return duration(self.last_datetime(), now())


class ValidationError(Exception):
    def __init__(self, msg, i=None, line=None):
        self.i = i
        self.line = line
        super().__init__(msg, i=i, line=line)


class Trackfile:
    def __init__(self, p: str):
        self.last_time = None
        self.state = TrackfileState(p, parse_filename(p), None, False, False)
        with open(p) as f:
            for i, line in enumerate(f, start=1):
                self.parse(i, line)

        if not self.state.finished:
            self.state.active_lasttime = self.last_time
        self.last_time = None

    def parse(self, i: int, line: str):
        line = line.strip()
        if not line:
            return
        if "FINISHED" in line:
            log.debug('found FINISHED line: "%s"', line)
            self.state.finished = True
        if "EXPORTED" in line:
            log.debug('found EXPORTED line: "%s"', line)
            self.state.exported = True

        time_match = time_re().match(line)
        if time_match:
            log.debug('found time line: "%s"', line)
            last_time = time_match.group("last_time")
            last_time = parse_time(last_time)
            if self.last_time is not None:
                if self.last_time > last_time:
                    # fmt:off
                    raise ValidationError(f"Unordered lines; entry ending at {self.last_time} was detected before an entry ending at {last_time}", i=i, line=line)  # noqa
            self.last_time = last_time


@lru_cache()
def time_re():
    return re.compile(TIME_RE_TXT)


def parse_time(t) -> datetime.time:
    h = int(t[0:2])
    m = 0
    if len(t) == 5:
        m = int(t[3:5])
    return datetime.time(h, m)


def parse_filename(f: str) -> datetime.date:
    f = os.path.basename(f)
    if f.endswith('.today.easytrack'):
        f = f[:-16]
    elif f.endswith('.easytrack'):
        f = f[:-10]

    return datetime.datetime.strptime(f, '%Y.%m.%d').date()
