import dataclasses
import json
from pathlib import Path


def to_json(x):
    return json.dumps(make_serializable(x))


def to_json_file(x, f, raw=True, indent=None):
    if not raw:
        x = make_serializable(x)
    json.dump(x, f, indent=indent)
    f.write("\n")


def make_serializable(x):
    if dataclasses.is_dataclass(x):
        x = dataclasses.asdict(x)

    if isinstance(x, dict):
        return {k: make_serializable(v) for (k, v) in x.items()}
    if isinstance(x, list):
        return [make_serializable(v) for v in x]
    if isinstance(x, Path):
        return str(x)
    return x
