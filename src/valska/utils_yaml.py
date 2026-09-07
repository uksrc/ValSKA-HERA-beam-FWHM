from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# -----------------------------------------------------------------------------
# YAML IO (ruamel.yaml)
# -----------------------------------------------------------------------------

_YAML = YAML(typ="rt")  # round-trip
_YAML.preserve_quotes = True
_YAML.indent(mapping=2, sequence=4, offset=2)
_YAML.width = 4096


def load_yaml(path: Path) -> CommentedMap:
    """Load a YAML file preserving comments and formatting."""
    with path.open("r", encoding="utf-8") as f:
        data = _YAML.load(f)
    if not isinstance(data, CommentedMap):
        raise ValueError(f"Expected a mapping at top-level of YAML: {path}")
    return data


def dump_yaml(data: Mapping[str, Any], path: Path) -> None:
    """Write YAML using ruamel round-trip formatting."""
    if isinstance(data, CommentedMap):
        out = data
    else:
        out = CommentedMap(dict(data))

    with path.open("w", encoding="utf-8") as f:
        _YAML.dump(out, f)
