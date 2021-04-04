import logging
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from subprocess import PIPE, SubprocessError
from time import sleep

from easytrack.jsonfmt import to_json_file
from easytrack.time import now, round_time

log = logging.getLogger(__name__)

WMCTRL_L_X_REGEXIK = r"(?P<window_id>\S+)\s+(?P<desktop_id>\d+)\s+(?P<wm_class>\S+)\s+(?P<host>\S+)\s+(?P<window_title>\S.*)$"


class EventException(Exception):
    pass


@dataclass(frozen=True)
class MonitorState:
    ticks: int
    output_filename_rotate_frequency_minutes: int
    output_dir: Path

    def gen_output_path(self) -> Path:
        ts = now()
        ts = round_time(ts, self.output_filename_rotate_frequency_minutes)
        return self.output_dir / f"monitor.{ts.isoformat('_', 'minutes')}.log"

    def run_monitor(self):
        self.output_dir.mkdir(exist_ok=True)
        log.info("starting monitor: %s", repr(self))
        ntry = 0
        while ntry < self.ticks:
            ntry += 1
            ts = now()
            sleep_duration = 1 - ts.microsecond / (10 ** 6)
            if sleep_duration < 0.5:
                sleep_duration += 1
                ntry += 1
            sleep(sleep_duration)
            ts = now()
            try:
                with self.gen_output_path().open("a") as output_file:
                    to_json_file(
                        {
                            "type": "meta",
                            "timestamp": ts.isoformat(sep="_", timespec="milliseconds"),
                        },
                        output_file,
                    )
                    to_json_file(_grab_wmctrl_all_windows(), output_file)
                    to_json_file(_grab_wmctrl_all_desktops(), output_file)
                    to_json_file(_get_xprintidle(), output_file)
                    to_json_file(_get_xdotool_active_window(), output_file)

            except SubprocessError:
                logging.exception("subprocess error - continuing in 1s")
            except EventException:
                logging.exception("event exception - continuing in 1s")

        log.info("ending monitor")


def _grab_wmctrl_all_windows():
    res_rows = []
    wmctrl_res = subprocess.run(["wmctrl", "-l", "-x"], stdout=PIPE, check=True,)
    lines = wmctrl_res.stdout.decode().strip().split("\n")
    for line in lines:
        line_match = _wmctrl_l_x_re().match(line)
        if not line_match:
            raise EventException("Wrong wmctrl -l -x line", line)
        res = {
            "window ID": line_match.group("window_id"),
            "desktop ID": line_match.group("desktop_id"),
            "WM_CLASS": line_match.group("wm_class"),
            "window title": line_match.group("window_title"),
        }
        res_rows.append(res)
    return {"type": "wmctrl_windows", "windows": res_rows}


def _grab_wmctrl_all_desktops():
    res_rows = []
    wmctrl_res = subprocess.run(["wmctrl", "-d"], stdout=PIPE, check=True)
    lines = wmctrl_res.stdout.decode().strip().split("\n")
    for line in lines:
        res = {"desktop ID": line.split(" ", 2)[0], "desktop title": line[35:]}
        res_rows.append(res)
    return {"type": "wmctrl_desktops", "desktops": res_rows}


def _get_xprintidle():
    wmctrl_res = subprocess.run(["xprintidle"], stdout=PIPE, check=True)
    lines = wmctrl_res.stdout.decode().strip()
    try:
        return {"type": "xprintidle", "idle_msecs": int(lines)}
    except TypeError:
        raise EventException(f"Couldn't parse idle time: {lines}")


def _get_xdotool_active_window():
    window_id = _get_xdotool_active_window_id()
    return {
        "type": "xdotool_active_window",
        "window ID": window_id,
        "window title": _get_xdotool_window_name(window_id),
    }


def _get_xdotool_active_window_id():
    wmctrl_res = subprocess.run(["xdotool", "getactivewindow"], stdout=PIPE, check=True)
    lines = wmctrl_res.stdout.decode().strip()
    try:
        return int(lines)
    except TypeError:
        raise EventException(f"Couldn't parse as window id: {lines}")


def _get_xdotool_window_name(window_id: int):
    wmctrl_res = subprocess.run(
        ["xdotool", "getwindowname", str(window_id)], stdout=PIPE, check=True
    )
    lines = wmctrl_res.stdout.decode().strip()
    return lines


@lru_cache()
def _wmctrl_l_x_re():
    return re.compile(WMCTRL_L_X_REGEXIK)
