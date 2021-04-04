from dataclasses import dataclass
import json
from pathlib import Path
from typing import Union, List

from easytrack.jsonfmt import to_json_file


@dataclass
class Alias:
    alias: Union[str, List[str]]
    project: str
    task: str

    def aliases(self):
        if isinstance(self.alias, str):
            return [self.alias]
        return self.alias


class AliasDB:
    """A user-managed DB with task aliases"""

    def __init__(self, db_path: Union[Path, str]):
        self.db_path = Path(db_path)

    def file_exists(self):
        return self.db_path.exists()

    def replace_aliases(self, aliases: List[Alias]):
        data = {"aliases": aliases}
        write_path = Path(str(self.db_path) + ".write")
        with write_path.open("w") as f:
            to_json_file(data, f, raw=False, indent=4)
        write_path.rename(self.db_path)

    def get_aliases(self):
        if self.file_exists():
            with self.db_path.open("r") as f:
                data = json.load(f)
                tasks = [Alias(**x) for x in data["aliases"]]
            return tasks
        else:
            return None


if __name__ == "__main__":
    db = AliasDB("/home/ks/workdir/trackdir/toggl_aliases.json")
    # some_alias = Alias(alias=['dev'], project='Engineering', task='Build task DEFAULT')
    # db.replace_aliases([some_alias])
    aliases = db.get_aliases()
    print(aliases)
