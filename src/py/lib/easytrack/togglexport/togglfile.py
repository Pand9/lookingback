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
                log.exception(f'Validation error: {e}')
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
        description = time_match["desc"]

        if len(tags) != 1:
            raise ValidationError(f"Expected one tag, got {tags}")

        alias = self.aliases.get(tags[0])
        if alias is None:
            raise ValidationError(
                f"Alias \"{tags[0]}\" not found. Available aliases: {list(self.aliases)}"
            )

        entry = TglStandardEntry(
            start=first_dtime,
            duration=duration,
            ptask_alias=tags[0],
            project=alias.project,
            task=alias.task,
            description=description,
        )
        self.res.entries_unchecked.append(entry)

    def _parse_line(self, i: int, line: str):
        try:
            if line[0] == "#":
                return
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
        res = date_expr().parseString(line, parseAll=True)
    except pp.ParseException:
        return None
    return datetime.date(int(res.year), int(res.month), int(res.day))


@lru_cache()
def date_expr():
    num2 = pp.Word(pp.nums, min=2, max=2)
    num4 = pp.Word(pp.nums, min=4, max=4)
    date = (
        num4.setResultsName("year")
        + "-"
        + num2.setResultsName("month")
        + "-"
        + num2.setResultsName("day")
    )
    return date


def is_timeentry(line):
    return pp.Char(pp.nums).matches(line, parseAll=False)


def try_parse_timeentry(line):
    res = timeentry_expr().parseString(line, parseAll=True)
    return {
        "tags": list(res.tag),
        "desc": " ".join([d.strip() for d in res.desc]).strip(),
        "first_time": datetime.time(int(res.start_hour), int(res.start_minute))
        if res.start_hour
        else None,
        "last_time": datetime.time(int(res.end_hour), int(res.end_minute))
        if res.end_hour
        else None,
        "hours": int(res.hours) if res.hours else None,
        "minutes": int(res.minutes) if res.minutes else None,
    }


@lru_cache()
def timeentry_expr():
    num2 = pp.Word(pp.nums, exact=2)
    start_time = (
        num2.setResultsName("start_hour") + ":" + num2.setResultsName("start_minute")
    )
    duration_sep = pp.Optional(pp.Word("-"))
    end_time = num2.setResultsName("end_hour") + ":" + num2.setResultsName("end_minute")

    interval_h = pp.Word(pp.nums).setResultsName("hours") + "h"
    interval_m = pp.Word(pp.nums).setResultsName("minutes") + "m"
    end = pp.Or([interval_h, interval_m, interval_h + interval_m, end_time])

    desc_sep = "|"
    desc = tags_expr()

    return pp.Optional(start_time + duration_sep) + end + desc_sep + desc


def parse_tags(text):
    res = tags_expr().parseString(text)
    return list(res.tag), " ".join(res.desc)


@lru_cache()
def tags_expr():
    desc = pp.CharsNotIn("[]").setResultsName("desc", True)
    tag = pp.CharsNotIn("[]").setResultsName("tag", True)
    res = pp.Optional(desc) + pp.ZeroOrMore("[" + tag + "]" + pp.Optional(desc))
    return res


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
