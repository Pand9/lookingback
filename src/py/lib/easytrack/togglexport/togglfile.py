import datetime
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Tuple

import pyparsing as pp
from easytrack.togglexport.alias_db import Alias, AliasDB
from easytrack.togglexport.entry import TglStandardEntry
from easytrack.trackfile import parse_time

log = logging.getLogger(__name__)


@dataclass
class Togglfile:
    entries_unchecked: List[TglStandardEntry]
    comments: List[Tuple[int, str]]
    errors: List["ValidationError"]

    def get_dates(self):
        dates = {e.start.date() for e in self.entries}
        return sorted(dates)

    @property
    def entries(self):
        if self.errors:
            raise self.errors[0]
        return self.entries_unchecked


class ValidationError(Exception):
    def __init__(self, msg, i=None, line=None):
        self.i = i
        self.line = line
        super().__init__(msg)

    def __str__(self):
        return f"{super().__str__()}; line number: {self.i}; line: {self.line}"


def parse_toggl_file(
    content: str, aliases: List[Alias], file_date: Optional[datetime.date] = None
) -> Togglfile:
    parser = _TogglfileParser(content, aliases, file_date)
    return parser.parse()


class _TogglfileParser:
    def __init__(
        self,
        content: str,
        aliases: List[Alias],
        file_date: Optional[datetime.date] = None,
    ):
        self.content = content
        self.res = Togglfile([], [], [])

        self.file_date = file_date
        self.date = self.file_date
        self.res.comments.append((0, f"set date to {self.date}"))

        self.aliases = {val: alias for alias in aliases for val in alias.aliases()}

    def parse(self):
        for i, line in enumerate(self.content.strip().split("\n"), start=1):
            try:
                line = line.strip()
                if line:
                    self._parse_line(i, line)
            except ValidationError as e:
                log.exception(f"Validation error: {e}")
                self.res.errors.append(e)
        return self.res

    def _parse_time(self, first_time, last_time, hours, minutes, **_):
        if first_time is None:
            first_time = datetime.time()
        first_dtime = datetime.datetime.combine(self.date, first_time)
        if last_time is not None:
            last_dtime = datetime.datetime.combine(self.date, parse_time(last_time))
            if last_dtime < first_dtime:
                last_dtime += datetime.timedelta(days=1)
            duration = last_dtime - first_dtime
        else:
            if hours is None and minutes is None:
                raise ValidationError("end time, or duration, is missing", None, None)
            if hours is None:
                hours = "0"
            if minutes is None:
                minutes = "0"
            duration = datetime.timedelta(hours=int(hours), minutes=int(minutes))
        return first_dtime, duration

    def _parse_timeentry_line(self, time_match):
        first_dtime, duration = self._parse_time(**time_match)

        tags = time_match["tags"]
        if len(tags) != 1:
            raise ValidationError(f"Expected one tag, got {tags}")
        tag = tags[0]
        del tags

        description = time_match["desc"]

        alias = self.aliases.get(tag)
        if alias is None:
            raise ValidationError(
                f'Alias "{tag}" not found. Available aliases: {list(self.aliases)}'
            )

        entry = TglStandardEntry(
            start=first_dtime,
            duration=duration,
            ptask_alias=tag,
            project=alias.project,
            task=alias.task,
            description=description,
        )
        self.res.entries_unchecked.append(entry)

    def _parse_line(self, i: int, line: str):
        try:
            date_match = try_parse_date(line)
            if date_match:
                self.date = date_match
                self.res.comments.append((i, f"Set date to {self.date}"))
                return
            if is_timeentry(line):
                time_match = try_parse_timeentry(line)
                return self._parse_timeentry_line(time_match)

        except ValidationError as e:
            e.line = line
            e.i = i
            raise
        except Exception as e:
            raise ValidationError(f"{str(type(e))}: {e}", i=i, line=line) from e


def try_parse_date(line):
    try:
        res = date_expr().parseString(line, parseAll=False)
    except pp.ParseException:
        return None
    return datetime.date(int(res.year), int(res.month), int(res.day))


def date_expr():
    return (
        pp.Word(pp.nums).setResultsName("year")
        + "-"
        + pp.Word(pp.nums).setResultsName("month")
        + "-"
        + pp.Word(pp.nums).setResultsName("day")
    )


def is_timeentry(line):
    return pp.Char(pp.nums).matches(line, parseAll=False)


def try_parse_timeentry(line):
    res = timeentry_expr().parseString(line, parseAll=True)
    return {
        "tags": list(res.tag),
        "desc": res.desc.strip(),
        "first_time": parse_time(res.first_time[0]) if res.first_time else None,
        "last_time": parse_time(res.last_time[0]) if res.last_time else None,
        "hours": int(res.hours) if res.hours else None,
        "minutes": int(res.minutes) if res.minutes else None,
    }


TAG_SYMBOLS = pp.alphanums + "_"


@lru_cache()
def timeentry_expr():
    start_time = (
        pp.Word(pp.nums) + pp.Optional(":" + pp.Word(pp.nums))
    ).setResultsName('first_time')
    end_time = (
        pp.Word(pp.nums) + pp.Optional(":" + pp.Word(pp.nums))
    ).setResultsName("last_time")

    interval_h = pp.Word(pp.nums).setResultsName("hours") + "h"
    interval_m = pp.Word(pp.nums).setResultsName("minutes") + "m"

    timepart = pp.Or(
        (
            start_time + pp.Char("-") + end_time,
            pp.Optional(start_time)
            + pp.Or((interval_h, interval_m, interval_h + interval_m)),
        )
    )
    tagpart = (
        pp.Optional(pp.CharsNotIn(TAG_SYMBOLS))
        + pp.Word(TAG_SYMBOLS).setResultsName("tag", listAllMatches=True)
        + pp.Optional(pp.CharsNotIn(TAG_SYMBOLS))
    )
    descpart = pp.SkipTo(pp.lineEnd).setResultsName("desc")

    return timepart + tagpart + descpart


if __name__ == "__main__":
    content = """
2021-04-02
11:00 5h 15m | [dev] dfa
20m | [dev] ggh
2021-03-03
3h | ggh [planning]
    """
    db = AliasDB("/home/ks/workdir/trackdir/toggl_aliases.json")
    aliases = db.get_aliases()
    res = parse_toggl_file(content, aliases)
    for entry in res.entries:
        print(entry)
