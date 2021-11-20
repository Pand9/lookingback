import datetime
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Tuple

import pyparsing as pp
from easytrack.togglexport.alias_db import Alias, AliasDB
from easytrack.togglexport.entry import TglStandardEntry
from easytrack.trackfile import parse_time

log = logging.getLogger(__name__)


@dataclass
class Togglfile:
    dates_unchecked: List[Tuple[datetime.date, datetime.date]]
    entries_unchecked: List[TglStandardEntry]
    comments: List[Tuple[int, str]]
    errors: List["ValidationError"]

    def get_dates_unchecked(self):
        return sorted(
            {
                d
                for (first, last) in self.dates_unchecked
                for d in iterdates(first, last)
            }
        )

    def get_dates(self):
        if self.errors:
            raise self.errors[0]
        return self.get_dates_unchecked()

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


def parse_toggl_file(content: str, aliases: List[Alias]) -> Togglfile:
    parser = _TogglfileParser(content, aliases)
    return parser.parse()


def iterdates(date, last):
    assert date <= last, (date, last)
    while True:
        yield date
        if date == last:
            break
        date += datetime.timedelta(days=1)


class _TogglfileParser:
    def __init__(self, content: str, aliases: List[Alias]):
        self.content = content
        self.res = Togglfile([], [], [], [])

        self.aliases = {val: alias for alias in aliases for val in alias.aliases()}

    @property
    def dates(self):
        try:
            return self.res.dates_unchecked[-1]
        except IndexError:
            raise ValidationError("Date has not been set before time entry")

    def iterdates(self):
        return iterdates(*self.dates)

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
        for date in self.iterdates():
            if first_time is None:
                first_time = datetime.time()
            first_dtime = datetime.datetime.combine(date, first_time)
            if last_time is not None:
                last_dtime = datetime.datetime.combine(date, parse_time(last_time))
                if last_dtime < first_dtime:
                    last_dtime += datetime.timedelta(days=1)
                duration = last_dtime - first_dtime
            else:
                if hours is None and minutes is None:
                    raise ValidationError("end time, or duration, is missing")
                if hours is None:
                    hours = "0"
                if minutes is None:
                    minutes = "0"
                duration = datetime.timedelta(hours=int(hours), minutes=int(minutes))
            yield first_dtime, duration

    def _parse_timeentry_line(self, time_match):
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

        for first_dtime, duration in self._parse_time(**time_match):
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
            date_match = try_parse_dates(line)
            if date_match:
                first_date, last_date = date_match
                if first_date > last_date:
                    raise ValidationError("Wrong order of pair of dates")
                self.res.dates_unchecked.append((first_date, last_date))  # type:ignore
                self.res.comments.append((i, f"Set dates to {self.dates}"))
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


def try_parse_dates(line):
    try:
        res = dates_expr().parseString(line, parseAll=False)
    except pp.ParseException:
        return None
    start_date = "".join(res.start_date)
    end_date = "".join(res.end_date) if res.end_date else start_date
    return (
        datetime.datetime.strptime(start_date, "%Y-%m-%d").date(),
        datetime.datetime.strptime(end_date, "%Y-%m-%d").date(),
    )


def dates_expr():
    # fmt:off
    dtexpr = (
        pp.Word(pp.nums) +
        "-" + pp.Word(pp.nums) +
        "-" + pp.Word(pp.nums)
    )
    return (
        dtexpr.setResultsName('start_date') +
        pp.Optional(
            "-" + dtexpr.setResultsName('end_date')
        )
    )
    # fmt:on


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
    # fmt:off
    start_time = (
        pp.Word(pp.nums) + pp.Optional(":" + pp.Word(pp.nums))
    ).setResultsName("first_time")
    end_time = (
        pp.Word(pp.nums) + pp.Optional(":" + pp.Word(pp.nums))
    ).setResultsName("last_time")

    interval_h = pp.Word(pp.nums).setResultsName("hours") + pp.Char("h")
    interval_m = pp.Word(pp.nums).setResultsName("minutes") + pp.Char("m")

    timepart = pp.Or([
        start_time + pp.Char("-") + end_time,
        pp.Or([
            interval_h,
            interval_m,
            interval_h + interval_m
        ])
    ])
    timeseppart = pp.Optional(pp.Char('|:-'))
    tagpart = (
        pp.Char('[')
        + pp.CharsNotIn('[]').setResultsName("tag", listAllMatches=True)
        + pp.Char(']')
    )
    descpart = pp.SkipTo(pp.lineEnd).setResultsName("desc")

    return timepart + timeseppart + pp.OneOrMore(tagpart) + descpart
    # fmt:on


if __name__ == "__main__":
    content = """
2021-04-02 - 2021-04-05
11:00 - 15:00 | [dev] dfa
20m | [dev] ggh
2021-03-03
3h |[planning] ggh
11 - 13 |[planning] ggh
    """
    db = AliasDB("/home/ks/workdir/trackdir/toggl_aliases.json")
    aliases = db.get_aliases()
    res = parse_toggl_file(content, aliases)
    for entry in res.entries:
        print(entry)
