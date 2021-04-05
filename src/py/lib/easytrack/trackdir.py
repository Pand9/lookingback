import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from easytrack.conf import Conf
from easytrack.time import now, today
from easytrack.trackfile import Trackfile, TrackfileState

log = logging.getLogger(__name__)


@dataclass
class TrackdirState:
    dirpath: Path
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


class Trackdir:
    def __init__(self, conf: Conf):
        self.state = TrackdirState(dirpath=conf.track_dir, actives=None)
        active_dir = conf.track_dir / "active"
        finished_dir = conf.track_dir / "finished"
        exported_dir = conf.track_dir / "exported"

        for d in active_dir, finished_dir, exported_dir:
            d.mkdir(exist_ok=True)

        for p in self.state.exportstatus_file(), self.state.exporting_file():
            if not p.exists():
                p.open("w").close()

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

        with self.state.today_trackfile_path().open("a"):
            log.debug("ensure .today.easytrack")
            pass

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

        self.state.actives = active_trackfiles

        from easytrack.statusfile import rewrite_statusfile

        log.debug("conf: %s", repr(conf))
        log.debug("trackdir: %s", repr(self.state))

        rewrite_statusfile(conf, self)


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
