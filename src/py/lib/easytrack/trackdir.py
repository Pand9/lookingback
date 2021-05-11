import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from easytrack.conf import Conf
from easytrack.time import now, today
from easytrack.togglexport.task_db import TaskDB
from easytrack.trackfile import Trackfile, TrackfileState

log = logging.getLogger(__name__)


@dataclass
class TrackdirStateBeforeValidation:
    dirpath: Path

    def activedir(self) -> Path:
        return self.dirpath / "active"

    def paths_to_open(self, conf: Conf):
        return [conf.conf_path]


@dataclass
class TrackdirToggl(TrackdirStateBeforeValidation):
    def toggl_taskcache_path(self) -> Path:
        return self.dirpath / "toggl_task_cache.json"

    def toggl_aliases_path(self) -> Path:
        return self.dirpath / "toggl_aliases.json"

    def exportstatus_file(self) -> Path:
        return self.dirpath / "export_status.md"

    def exporting_file(self) -> Path:
        return self.activedir() / "export_input.easyexport"

    @classmethod
    def init_novalidate(cls, conf: Conf) -> "TrackdirToggl":
        return cls(dirpath=conf.track_dir)

    @classmethod
    def init(cls, conf: Conf) -> "TrackdirToggl":
        state = TrackdirToggl(dirpath=conf.track_dir)
        state.activedir().mkdir(exist_ok=True)

        for p in state.exportstatus_file(), state.exporting_file():
            if not p.exists():
                p.open("w").close()

        return state

    def download_tasks(self):
        TaskDB(self.toggl_taskcache_path()).cache_refresh()

    def paths_to_open(self, conf: Conf):
        return [
            self.exporting_file(),
            self.exportstatus_file(),
            self.toggl_aliases_path(),
            conf.conf_path,
        ]


@dataclass
class TrackdirTrackfiles(TrackdirStateBeforeValidation):
    actives: List[TrackfileState]

    def today_trackfile(self) -> Path:
        res = [f for f in self.actives if f.day == today()]
        return res[0] if res else None

    def activedir(self) -> Path:
        return self.dirpath / "active"

    def today_trackfile_path(self) -> Path:
        return self.dirpath / "active" / today().strftime("%Y.%m.%d.today.easytrack")

    def statusfile_path(self) -> Path:
        return self.dirpath / "status.md"

    def exportstatus_file(self) -> Path:
        return self.dirpath / "export_status.md"

    def exporting_file(self) -> Path:
        return self.activedir() / "export_input.easyexport"

    def toggl_taskcache_path(self) -> Path:
        return self.dirpath / "toggl_task_cache.json"

    def toggl_aliases_path(self) -> Path:
        return self.dirpath / "toggl_aliases.json"

    @classmethod
    def init_novalidate(cls, conf: Conf) -> "TrackdirTrackfiles":
        state = TrackdirTrackfiles(conf.track_dir, actives=[])
        state.activedir().mkdir(exist_ok=True)
        with state.today_trackfile_path().open("a"):
            log.debug("ensure .today.easytrack")
        return state

    @classmethod
    def init(cls, conf: Conf) -> "TrackdirTrackfiles":
        state = cls.init_novalidate(conf)
        active_dir = state.activedir()
        finished_dir = conf.track_dir / "finished"
        exported_dir = conf.track_dir / "exported"
        for d in active_dir, finished_dir, exported_dir:
            d.mkdir(exist_ok=True)

        active_trackfiles = []

        for p in finished_dir.iterdir():
            if str(p).endswith("dup.easytrack"):
                log.debug("skipping dup file: %s", p)
                continue
            if not str(p).endswith(".easytrack"):
                continue
            f = Trackfile(p)
            if f.state.exported:
                rename(p, "exported")

        with state.today_trackfile_path().open("a"):
            log.debug("ensure .today.easytrack")

        for p in active_dir.iterdir():
            if str(p).endswith("dup.easytrack"):
                log.debug("skipping dup file: %s", p)
                continue
            if not str(p).endswith(".easytrack"):
                continue
            f = Trackfile(p).state
            if f.exported:
                log.debug("rename exported: %s", p)
                rename(p, "exported")
            elif f.finished:
                log.debug("rename finished: %s", p)
                rename(p, "finished")
            elif str(p).endswith(".today.easytrack") and f.day != today():
                log.debug("rename .today.easytrack")
                new_p = rename(p, "active")
                active_trackfiles.append(Trackfile(new_p).state)
            else:
                log.debug("remains active: %s", p)
                active_trackfiles.append(f)

        active_trackfiles.sort(key=lambda f: f.day, reverse=True)
        return TrackdirTrackfiles(dirpath=state.dirpath, actives=active_trackfiles)

    def paths_to_open(self, conf: Conf):
        if self.actives:
            active_paths = [f.path for f in self.actives]
        else:
            active_paths = sorted(
                (
                    f
                    for f in self.activedir().iterdir()
                    if str(f).endswith(".easytrack")
                ),
                reverse=True,
            )
        return [*active_paths, self.statusfile_path(), conf.conf_path]


def rename(p, target: str):
    assert target in ("active", "finished", "exported"), target
    p = str(p)
    base_p, name = os.path.split(p)
    base_p, source = os.path.split(base_p)

    new_name = name
    if name.endswith(".today.easytrack"):
        new_name = str(name)[:-16] + ".easytrack"

    new_p = os.path.join(base_p, target, new_name)
    if os.path.exists(new_p):
        new_p_dup = f"{new_p}.{now().isoformat()}.dup.easytrack"
        log.debug("renaming: %s to %s", new_p, new_p_dup)
        os.rename(new_p, new_p_dup)
    os.rename(p, new_p)
    return new_p
