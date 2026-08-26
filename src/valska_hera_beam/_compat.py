"""Compatibility helpers for the deprecated ``valska_hera_beam`` package."""

from __future__ import annotations

import warnings


def warn_import(old_name: str, new_name: str | None = None) -> None:
    """Emit a deprecation warning for legacy import paths."""
    target = new_name or old_name.replace("valska_hera_beam", "valska", 1)
    warnings.warn(
        (
            f"`{old_name}` is deprecated and will be removed in a future release. "
            f"Use `{target}` instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
