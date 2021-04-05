import datetime
from dataclasses import dataclass, field, replace


@dataclass(order=True, frozen=True)
class TglStandardEntry:
    start: datetime.datetime
    duration: datetime.timedelta
    ptask_alias: str = field(compare=False)
    project: str
    task: str
    description: str

    def normalize(self):
        if self.duration.days:
            raise Exception(f"Nonzero days in time entry {self}")
        return replace(self, start=self.start.astimezone().replace(tzinfo=None))

    def __str__(self):
        end = self.start + self.duration
        datestr = self.start.strftime("%Y-%m-%d")
        startstr = self.start.strftime("%H:%M")
        endstr = end.strftime("%H:%M")
        tzstr = self.start.strftime("%z")
        timestr = f"{datestr} {startstr} - {endstr}"
        if tzstr:
            timestr += f" {tzstr}"
        aliasstr = f"[{self.ptask_alias}]"
        if not self.task:
            taskstr = f"({self.project})"
        else:
            taskstr = f"({self.project}, {self.task})"
        return f"{timestr} {aliasstr} {taskstr} {self.description}"
