import toml
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True, eq=True)
class Conf:
    conf_path: Path
    track_dir: Path


def load_conf() -> Conf:
    track_dir = os.getenv('EASYTRACK_TRACK_DIR')
    if not track_dir:
        track_dir = '~/trackdir'
    track_dir = Path(track_dir).expanduser()
    track_dir.mkdir(exist_ok=True)
    conf_path = track_dir / 'config.toml'
    if not conf_path.exists():
        conf_path.write_text("")
    conf = toml.load(str(conf_path))
    conf = Conf(conf_path=conf_path, track_dir=track_dir)
    return conf
