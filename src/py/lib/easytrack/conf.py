import toml
from dataclasses import dataclass
from pathlib import Path
import os


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
    conf_path = "~/.config/easytrack/config.toml"
    conf_path = os.path.expanduser(conf_path)
    conf = toml.load(conf_path)
    conf = validate_conf(Path(conf_path), conf)
    return conf
