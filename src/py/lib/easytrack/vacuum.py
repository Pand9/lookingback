import datetime
import enum
import logging
import os
from zipfile import ZIP_LZMA, ZipFile

from easytrack.conf import Conf


log = logging.getLogger(__name__)


class Word(enum.Enum):
    def __str__(self):
        return self.name.lower()


class Verb(Word):
    DELETE = enum.auto()
    ARCHIVE = enum.auto()


class Desc(Word):
    ALL = enum.auto()
    OLD = enum.auto()

    def __str__(self):
        return self.name.lower()


class Adv(Word):
    MONITS = enum.auto()
    LOGS = enum.auto()

    def __str__(self):
        return self.name.lower()


def do_vacuum(conf: Conf, verb, desc, advs, dry_run: bool):
    for adv in advs:
        _do_vacuum(
            conf, Verb[verb.upper()], Desc[desc.upper()], Adv[adv.upper()], dry_run
        )


def _do_vacuum(conf: Conf, verb: Verb, desc: Desc, adv: Adv, dry_run: bool):
    if dry_run:
        log.info(f"Dry-run: {verb} {desc} {adv}")
    if adv == Adv.MONITS:
        log_paths = [conf.track_dir / "monitor"]
        archive_paths = [conf.track_dir / "archive" / "monits"]
    elif adv == Adv.LOGS:
        log_paths = [conf.track_dir / "logs"]
        archive_paths = [conf.track_dir / "archive" / "logs"]
    else:
        raise ValueError(f"Unexpected adv {adv}")

    for log_path, archive_path in zip(log_paths, archive_paths):
        log_files = list(_scan_log_path(log_path))
        log_files = list(_filter(log_files, desc))
        if verb == Verb.DELETE:
            for tp, dtt, p in log_files:
                log.info(f"Deleting {p}")
                if not dry_run:
                    os.remove(p)
        elif verb == Verb.ARCHIVE:
            files_for_archive = dict()
            for tp, dtt, p in log_files:
                if tp:
                    f = f'{tp}.{dtt.strftime("%Y-%m")}.zip'
                else:
                    f = f'{dtt.strftime("%Y-%m")}.zip'
                ap = archive_path / f
                files_for_archive.setdefault(ap, []).append(p)
            _create_archives(files_for_archive, dry_run=dry_run)
        else:
            raise ValueError(f"Unexpected verb {verb}")


def _create_archives(files_for_archive, dry_run: bool):
    for archive_path, file_paths in files_for_archive.items():
        log.info(
            f"Putting {len(file_paths)} files in {archive_path} and deleting originals"
        )
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        f = ZipFile(archive_path, "a", compression=ZIP_LZMA) if not dry_run else None
        for p in file_paths:
            pb = os.path.basename(p)
            log.debug(f"Putting {p} in {archive_path} as {pb}")
            if not dry_run:
                f.write(p, pb)
        for p in file_paths:
            log.debug(f"Removing {p}")
            if not dry_run:
                os.remove(p)


def _scan_log_path(log_path):
    for first_path in os.scandir(log_path):
        if first_path.is_dir():
            for second_path in os.scandir(first_path.path):
                dtt = _parse_log_filename(second_path)
                if dtt:
                    yield (first_path.name, dtt, second_path.path)
        else:
            dtt = _parse_log_filename(first_path.path)
            if dtt:
                yield ("", dtt, first_path.path)


def _parse_log_filename(filepath):
    filename = os.path.basename(filepath)
    for f in "%Y-%m-%d.log", "monitor.%Y-%m-%d_%H:%M.log":
        try:
            return datetime.datetime.strptime(filename, "%Y-%m-%d.log")
        except ValueError:
            pass
    if filename.endswith(".easytrack"):
        return datetime.datetime.strptime(filename[:10], "%Y.%m.%d")
    if filename.endswith(".easyexport"):
        return
    log.debug(f"unrecognized file format {filepath}")


def _filter(log_files, desc: Desc):
    if desc == Desc.ALL:
        yield from log_files
        return
    elif desc != Desc.OLD:
        raise ValueError(f"Unexpected desc {desc}")
    d_ = (datetime.datetime.now() - datetime.timedelta(days=14)).replace(day=1).date()
    d = datetime.datetime(*d_.timetuple()[:3])
    for tp, dtt, p in log_files:
        if dtt < d:
            yield (tp, dtt, p)
