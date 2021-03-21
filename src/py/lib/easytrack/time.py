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


def round_time(dt: datetime.datetime, round_to_minutes: int) -> datetime.datetime:
    assert round_to_minutes in range(1, 61), f"expected 1-60, got {round_to_minutes}"
    dt = dt - datetime.timedelta(minutes=dt.minute % round_to_minutes)
    dt = dt.replace(second=0, microsecond=0)
    return dt
