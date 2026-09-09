"""Check registry: the extensibility mechanism for pre-flight checks.

Each check is a small function registered against a tier. Checks are
looked up and run by tier so a caller can choose how much to run (e.g.
"only the free/fast checks" vs "everything available").
"""

from __future__ import annotations

import traceback
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class CheckStatus(Enum):
    """Outcome of a single check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


class CheckTier(Enum):
    """Cost/availability tier a check belongs to.

    FAST checks only read file headers/metadata and never need a second
    file; they are cheap enough to always run. REFERENCE checks compare
    against a designated "known good" file and are skipped automatically
    when no reference is available. DEEP checks are more expensive
    (curve fits, delay-domain transforms) and are opt-in.
    """

    FAST = "fast"
    REFERENCE = "reference"
    DEEP = "deep"


@dataclass
class CheckResult:
    """The outcome of running one check against one file."""

    check_id: str
    status: CheckStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class CheckContext:
    """Input shared by all checks run against a single file.

    ``header`` and ``config_search_dirs`` are provided up front so
    individual checks don't each re-implement file reading or config
    discovery; checks that need more than this should read additional
    data themselves and cache it on ``extra``.
    """

    path: Path
    header: dict[str, Any]
    config_search_dirs: tuple[Path, ...] = ()
    reference_path: Path | None = None
    expected_beam_type: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


CheckFunc = Callable[[CheckContext], CheckResult]

_REGISTRY: dict[str, tuple[CheckFunc, CheckTier]] = {}


def register_check(
    check_id: str, tier: CheckTier
) -> Callable[[CheckFunc], CheckFunc]:
    """Decorator registering a function as a named, tiered check.

    Parameters
    ----------
    check_id :
        Stable identifier for this check, used in reports and to
        select/exclude checks. Must be unique across the registry.
    tier :
        Cost/availability tier this check belongs to.
    """

    def decorator(func: CheckFunc) -> CheckFunc:
        if check_id in _REGISTRY:
            raise ValueError(f"duplicate check_id: {check_id!r}")
        _REGISTRY[check_id] = (func, tier)
        return func

    return decorator


def _ensure_builtin_checks_imported() -> None:
    # Importing this module runs its @register_check decorators. Done
    # lazily (rather than at package import time) to avoid import-order
    # issues between registry.py and checks.py.
    import valska.data_preflight.checks  # noqa: F401


def list_checks(
    tiers: Iterable[CheckTier] | None = None,
) -> list[tuple[str, CheckTier]]:
    """List registered check IDs and their tiers, optionally filtered."""

    _ensure_builtin_checks_imported()
    tier_set = set(tiers) if tiers is not None else None
    return [
        (check_id, tier)
        for check_id, (_func, tier) in _REGISTRY.items()
        if tier_set is None or tier in tier_set
    ]


def run_checks(
    ctx: CheckContext,
    tiers: Iterable[CheckTier],
    *,
    check_ids: Iterable[str] | None = None,
) -> list[CheckResult]:
    """Run every registered check in the requested tier(s) against ``ctx``.

    A check that raises is recorded as a FAIL rather than propagating,
    so one broken check cannot prevent the rest of the report from
    being produced.
    """

    _ensure_builtin_checks_imported()
    tier_set = set(tiers)
    id_filter = set(check_ids) if check_ids is not None else None

    results: list[CheckResult] = []
    for check_id, (func, tier) in _REGISTRY.items():
        if tier not in tier_set:
            continue
        if id_filter is not None and check_id not in id_filter:
            continue
        try:
            results.append(func(ctx))
        except Exception as exc:  # noqa: BLE001
            results.append(
                CheckResult(
                    check_id=check_id,
                    status=CheckStatus.FAIL,
                    message=f"check raised an exception: {exc}",
                    details={"traceback": traceback.format_exc()},
                )
            )
    return results
