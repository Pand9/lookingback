import datetime
from typing import Optional


def now(round_to_minutes: Optional[int] = None):
    res = datetime.datetime.now()
    if round_to_minutes is not None:
        assert round_to_minutes in range(1, 61), f"expected 1-60, got {round_to_minutes}"
        res = res.replace(second=0, microsecond=0)
        res -= datetime.timedelta(minutes=res.minute % round_to_minutes)
    return res
