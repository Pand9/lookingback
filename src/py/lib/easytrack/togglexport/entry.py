from dataclasses import dataclass
import datetime
from typing import Optional


@dataclass
class TglStandardEntry:
    start: datetime.datetime
    duration: datetime.timedelta
    ptask_alias: str
    project: str
    task: Optional[str]
    description: str

    def validate(self):
        if self.duration.days:
            raise Exception(f"Nonzero days in time entry {self}")

    def __str__(self):
        end = self.start + self.duration
        datestr = self.start.strftime("%Y-%m-%d")
        startstr = self.start.strftime("%H:%M")
        endstr = end.strftime("%H:%M")
        tzstr = self.start.strftime("%z")
        timestr = f"{datestr} {startstr} - {endstr}"
        if tzstr:
            timestr += f' {tzstr}'
        taskstr = f"[{self.ptask_alias}] ({self.project}, {self.task})"
        return f"{timestr} {taskstr} {self.description}"
