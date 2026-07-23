"""Pre-flight inspection checks for incoming data files.

Runs cheap, self-contained checks against a data file (e.g. a UVH5
visibility file) before it is used in an expensive analysis such as a
BayesEoR sweep, so that mismatches between a file's recorded claims
about itself (filename, cited config) can be caught early. These
checks compare recorded metadata for internal consistency; they are
not a guarantee of what the file's data actually contain.
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
