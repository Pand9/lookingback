from easytrack.conf import Conf
from easytrack.time import today
from easytrack.trackdir import Trackdir
import datetime


def rewrite_statusfile(conf: Conf, trackdir: Trackdir):
    def _print(*a, **kw):
        print(*a, **kw, file=statusfile)

    curtime = datetime.datetime.now().time()

    with trackdir.state.statusfile_path().open("w") as statusfile:
        actives = trackdir.state.actives
        _print("# Easytrack status report")
        _print()
        _print("Generated:", curtime.isoformat(timespec="seconds"))

        _print()
        _print("## Tracking summary")
        _print()
        if not actives:
            _print("No active trackfiles")
        else:
            _print(
                f"Active trackfiles: {', '.join([_str_date(f.day) for f in actives])}",
            )
            lasttime = actives[0].active_lasttime
            d = actives[0].duration_from_lasttime()
            if d is not None:
                _print(
                    f"Time elapsed since last entry: {_mins(d)} minutes ({_hhmm(lasttime)} - {_hhmm(curtime)})"
                )
            else:
                _print("No entries found within active files.")

        _print()
        _print("## Guide to the trackfile format")
        _print()
        _print('- "FINISHED" anywhere within file moves the file to finished/ folder')
        _print('- "EXPORTED", similarly, moves the file to exported/ folder')
        _print('- Line starting with "HH:MM - HH:MM" is considered a time entry')
        _print('- "HH:MM" works too.')
        _print()
        _print(
            "Right-most time within a line is considered a finish time of the latest entry."
            " It's used to identify breaks from time tracking, which is then used to generate notifications,"
            " report system events from duration of the break, etc."
        )


def _hhmm(t):
    return t.isoformat(timespec="minutes")


def _mins(d):
    return d.seconds // 60


def _str_date(d):
    if d == today():
        return f"{d} (today)"
    return str(d)
