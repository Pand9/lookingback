import datetime
from dataclasses import dataclass
from functools import lru_cache
import re
import os
from pathlib import Path
from easytrack.time import duration, now
import logging
from typing import List, Optional

log = logging.getLogger(__name__)


# Explore it at: https://regex101.com/
TIME_RE_TXT = (
    r"\s*((?P<first_time>[0-9]+(:[0-9]+)?)\s*-\s*)?(?P<last_time>[0-9]+(:[0-9]+)?).*"
)


@dataclass(eq=True)
class TrackfileState:
    path: Path
    day: datetime.date
    last_datetime: Optional[datetime.datetime]
    finished: bool
    exported: bool
    errors: List["ValidationError"]

    def duration_from_lasttime(self) -> datetime.timedelta:
        if self.last_datetime is None:
            return None
        return duration(self.last_datetime, now())


class ValidationError(Exception):
    def __init__(self, msg, i=None, line=None):
        self.msg = msg
        self.i = i
        self.line = line
        super().__init__(msg)

    def __str__(self):
        return f"line {self.i}: {self.msg}"


class Trackfile:
    def __init__(self, p: str):
        self.state = TrackfileState(p, parse_filename(p), None, False, False, [])
        self.last_datetime = datetime.datetime.combine(self.state.day, datetime.time())
        with open(p) as f:
            for i, line in enumerate(f, start=1):
                self.parse(i, line)

        if not self.state.finished:
            self.state.last_datetime = self.last_datetime

    def parse(self, i: int, line: str):
        try:
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
                time_str = time_match.group("last_time")
                try:
                    time = parse_time(time_str)
                except ValueError:
                    raise ValidationError(f'Couldn\'t parse time "{time_str}"')
                dtt = datetime.datetime.combine(self.last_datetime.date(), time)
                if dtt < self.last_datetime:
                    if self.last_datetime - dtt <= datetime.timedelta(hours=12):
                        raise ValidationError(
                            f"Unordered lines: {self.last_datetime.time()} and {time}"
                        )
                    else:
                        dtt += datetime.timedelta(days=1)
                self.last_datetime = dtt
                log.debug('last_datetime updated to: "%s"', self.last_datetime)
        except ValidationError as e:
            e.i = i
            e.line = line
            log.info(f"Validation error {e}")
            self.state.errors.append(e)


@lru_cache()
def time_re():
    return re.compile(TIME_RE_TXT)


def parse_time(t) -> datetime.time:
    if isinstance(t, datetime.time):
        return t
    try:
        return datetime.datetime.strptime(t, "%H").time()
    except ValueError:
        pass
    try:
        return datetime.datetime.strptime(t, "%H:%M").time()
    except ValueError:
        raise


def parse_filename(f: str) -> datetime.date:
    f = os.path.basename(f)
    if f.endswith(".today.easytrack"):
        f = f[:-16]
    elif f.endswith(".easytrack"):
        f = f[:-10]

    return datetime.datetime.strptime(f, "%Y.%m.%d").date()
