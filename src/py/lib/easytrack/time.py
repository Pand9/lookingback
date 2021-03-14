import datetime
from functools import lru_cache


@lru_cache()
def today():
    return datetime.date.today()


def now():
    return datetime.datetime.now()


def duration(dt0: datetime.datetime, dt1: datetime.datetime) -> datetime.timedelta:
    assert dt0.tzinfo is None and dt1.tzinfo is None, (dt0, dt1)
    return dt1 - dt0
