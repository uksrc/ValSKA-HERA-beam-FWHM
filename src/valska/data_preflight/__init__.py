"""Pre-flight inspection checks for incoming data files.

Runs cheap, self-contained checks against a data file (e.g. a UVH5
visibility file) before it is used in an expensive analysis such as a
BayesEoR sweep, so mismatches between what a file claims to be and
what it actually contains can be caught early.
"""

from __future__ import annotations

from valska.data_preflight.registry import (
    CheckContext,
    CheckResult,
    CheckStatus,
    CheckTier,
    list_checks,
    run_checks,
)

__all__ = [
    "CheckContext",
    "CheckResult",
    "CheckStatus",
    "CheckTier",
    "list_checks",
    "run_checks",
]
