"""Access to bundled pyuvsim validation templates."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def list_templates() -> list[str]:
    """List shipped pyuvsim validation templates bundled with the package."""
    pkg = __package__  # valska.external_tools.pyuvsim.templates
    return sorted(
        [
            p.name
            for p in resources.files(pkg).iterdir()
            if Path(p.name).suffix in {".yaml", ".yml"}
        ]
    )


def get_template_path(name: str) -> Path:
    """
    Return a filesystem Path to a shipped template.

    Uses importlib.resources so this works both from a source checkout and from
    an installed wheel.
    """
    pkg = __package__
    candidate = resources.files(pkg) / name
    with resources.as_file(candidate) as p:
        return Path(p)
