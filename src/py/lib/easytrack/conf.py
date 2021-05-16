import toml
from dataclasses import dataclass
from pathlib import Path
import os


DEFAULT_BODY = '''
softlimit = 30
hardlimit = 120
'''.lstrip()


@dataclass(frozen=True, eq=True)
class Conf:
    conf_path: Path
    track_dir: Path
    softlimit: int
    hardlimit: int

    @classmethod
    def global_bash_scripts_dir(cls):
        res = os.getenv('EASYTRACK_BASH_SOURCE_PATH')
        if not res:
            raise ValueError('Please set $EASYTRACK_BASH_SOURCE_PATH')
        return res


def validate_conf(conf_path: Path, track_dir: Path, conf) -> Conf:
    return Conf(
        conf_path=conf_path,
        track_dir=track_dir,
        softlimit=int(conf["softlimit"]),
        hardlimit=int(conf["hardlimit"]),
    )


def load_conf() -> Conf:
    track_dir = os.getenv('EASYTRACK_TRACK_DIR')
    if not track_dir:
        raise ValueError('Please set $EASYTRACK_TRACK_DIR')
    track_dir = Path(track_dir).expanduser()
    conf_path = track_dir / 'config.toml'
    if not conf_path.exists():
        conf_path.write_text(DEFAULT_BODY)
    conf = toml.load(str(conf_path))
    conf = validate_conf(conf_path=conf_path, track_dir=track_dir, conf=conf)
    return conf
