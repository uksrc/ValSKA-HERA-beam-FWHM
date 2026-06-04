"""Compatibility tests for the canonical ``valska`` package rename."""

from __future__ import annotations

import importlib
import sys
import warnings
from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]


def _purge_modules(prefix: str) -> None:
    """Remove cached modules so import warnings can be asserted reliably."""
    for name in list(sys.modules):
        if name == prefix or name.startswith(f"{prefix}."):
            sys.modules.pop(name, None)


def test_legacy_top_level_import_warns_and_exposes_version():
    _purge_modules("valska_hera_beam")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        legacy = importlib.import_module("valska_hera_beam")

    assert legacy.__version__.strip() != ""
    assert any(
        "`valska_hera_beam` is deprecated" in str(w.message) for w in caught
    )


def test_legacy_nested_import_warns_and_keeps_api():
    _purge_modules("valska_hera_beam")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        legacy = importlib.import_module(
            "valska_hera_beam.external_tools.bayeseor.cli_submit"
        )

    assert callable(legacy.main)
    assert any(
        "valska_hera_beam.external_tools.bayeseor.cli_submit" in str(w.message)
        for w in caught
    )


def test_console_scripts_target_canonical_package():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    scripts = data["project"]["scripts"]

    assert scripts
    assert all(target.startswith("valska.") for target in scripts.values())
