import toml
from dataclasses import dataclass
from pathlib import Path
import os


DEFAULT_BODY = '''
track_dir = '~/workdir/trackdir'
softlimit = 30
hardlimit = 120
'''.lstrip()


@dataclass(frozen=True, eq=True)
class Conf:
    conf_path: Path
    track_dir: Path
    softlimit: int
    hardlimit: int


def validate_conf(conf_path: Path, conf) -> Conf:
    return Conf(
        conf_path=conf_path,
        track_dir=Path(os.path.expanduser(conf["track_dir"])),
        softlimit=int(conf["softlimit"]),
        hardlimit=int(conf["hardlimit"]),
    )


def load_conf() -> Conf:
    conf_path = Path(os.getenv('EASYTRACK_TRACK_DIR')) / 'config.toml'
    conf_path = conf_path.expanduser()
    if not conf_path.exists():
        conf_path.write_text(DEFAULT_BODY)
    conf = toml.load(str(conf_path))
    conf = validate_conf(Path(conf_path), conf)
    return conf
