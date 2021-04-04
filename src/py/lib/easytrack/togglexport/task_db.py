import datetime
import json
from pathlib import Path
from typing import Optional, Union

from easytrack.jsonfmt import to_json_file
from easytrack.togglexport.toggl_get_tasks import TglTask, toggl_get_tasks


class TaskDB:
    """Task DB with manually managed task cache"""

    def __init__(self, cache_path: Union[Path, str]):
        self.cache_path = Path(cache_path)

    def cache_exists(self):
        return self.cache_path.exists()

    def cache_get_lifetime(self) -> Optional[datetime.timedelta]:
        if self.cache_exists():
            mtime = datetime.datetime.fromtimestamp(self.cache_path.stat().st_mtime)
            return datetime.datetime.now() - mtime
        else:
            return None

    def cache_refresh(self):
        tasks = toggl_get_tasks()
        data = {"tasks": tasks}
        write_cache_path = Path(str(self.cache_path) + ".write")
        with write_cache_path.open("w") as f:
            to_json_file(data, f, raw=False, indent=4)
        write_cache_path.rename(self.cache_path)

    def get_tasks(self):
        if self.cache_exists():
            with self.cache_path.open("r") as f:
                data = json.load(f)
                tasks = [TglTask(**x) for x in data["tasks"]]
            return tasks
        else:
            return None


if __name__ == "__main__":
    tc = TaskDB("/home/ks/workdir/trackdir/toggl_task_cache.json")
    # tc.cache_refresh()
    tasks = tc.get_tasks()
    print(tasks)
