"""Built-in pre-flight checks.

Importing this module registers its checks with the registry in
registry.py (see ``@register_check`` below). Keep individual checks
small, dependency-light, and focused on one question each.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from valska.data_preflight.registry import (
    CheckContext,
    CheckResult,
    CheckStatus,
    CheckTier,
    register_check,
)

# Keyword -> canonical beam-type label. Mirrors the mapping
# valska.beam_metrics.TYPE_TO_CLASS uses for pyuvsim config "type"/"class"
# values, but this module intentionally does not import beam_metrics (it
# pulls in matplotlib/lmfit, which would make even the free/fast checks
# here dependency-heavy for no benefit).
_CONFIG_TYPE_LABELS: dict[str, str] = {
    "gaussian": "gaussian",
    "gaussianbeam": "gaussian",
    "airy": "airy",
    "airybeam": "airy",
    "uniform": "uniform",
    "uniformbeam": "uniform",
    "short_dipole": "short_dipole",
    "shortdipolebeam": "short_dipole",
}

# Keywords looked for directly in a file's own name/path, i.e. what the
# file's naming *claims* about its beam, independent of any config file.
# Matched against tokens split on non-alphanumeric characters (not a
# \b-boundary regex): file names delimit words with "_"/"-"/".", and \b
# does not treat "_" as a boundary, so "airy_quentin" would otherwise
# fail to match "airy".
_PATH_LABEL_KEYWORDS: dict[str, str] = {
    "gauss": "gaussian",
    "gaussian": "gaussian",
    "airy": "airy",
    "uniform": "uniform",
}
_TOKEN_SPLIT_RE = re.compile(r"[^a-zA-Z0-9]+")

_TELESCOPE_CONFIG_RE = re.compile(
    r"telescope_config/([\w.\-]+\.ya?ml)", re.IGNORECASE
)


class _SafeLoaderWithAnalyticBeamTag(yaml.SafeLoader):
    pass


def _analytic_beam_constructor(
    loader: yaml.SafeLoader, node: yaml.MappingNode
) -> dict[Any, Any]:
    return loader.construct_mapping(node)


_SafeLoaderWithAnalyticBeamTag.add_constructor(
    "!AnalyticBeam", _analytic_beam_constructor
)


def declared_beam_type(config_path: Path) -> str | None:
    """Return the canonical beam-type label a pyuvsim telescope config
    declares (e.g. "gaussian", "airy"), or None if it can't be determined.
    """

    try:
        with config_path.open(encoding="utf-8") as fh:
            values = yaml.load(fh, Loader=_SafeLoaderWithAnalyticBeamTag)
    except Exception:
        return None

    if not isinstance(values, dict):
        return None

    beam_paths = values.get("beam_paths")
    if not isinstance(beam_paths, dict) or 0 not in beam_paths:
        return None

    beam_entry = beam_paths[0]
    if not isinstance(beam_entry, dict):
        return None

    raw_label = beam_entry.get("class") or beam_entry.get("type")
    if not isinstance(raw_label, str):
        return None

    return _CONFIG_TYPE_LABELS.get(raw_label.strip().lower())


def path_claimed_beam_types(path: Path) -> set[str]:
    """Beam-type keywords found directly in the file's own name."""

    tokens = {
        token.lower() for token in _TOKEN_SPLIT_RE.split(path.name) if token
    }
    return {
        label
        for keyword, label in _PATH_LABEL_KEYWORDS.items()
        if keyword in tokens
    }


def find_cited_telescope_configs(history: str) -> list[str]:
    """Telescope-config filenames referenced in a UVH5 history string."""

    return _TELESCOPE_CONFIG_RE.findall(history or "")


def locate_config(filename: str, search_dirs: tuple[Path, ...]) -> Path | None:
    for search_dir in search_dirs:
        candidate = search_dir / filename
        if candidate.is_file():
            return candidate
    return None


_REQUIRED_METADATA_FIELDS = (
    "nants_telescope",
    "nants_data",
    "nbls",
    "ntimes",
    "nfreqs",
    "npols",
    "vis_units",
)


@register_check("metadata_summary", CheckTier.FAST)
def check_metadata_summary(ctx: CheckContext) -> CheckResult:
    """Report key ``/Header`` fields, flagging any that are absent.

    This reports on what ``inspect.read_uvh5_header`` already found; it
    cannot detect a header field that is present but wrong, only one
    that is missing from the header entirely. A field with an
    unreadable/non-numeric value causes ``read_uvh5_header`` itself to
    raise, which is surfaced as a file-level read error rather than a
    FAIL from this check.
    """

    header = ctx.header
    details = {
        "nants_telescope": header.get("nants_telescope"),
        "nants_data": header.get("nants_data"),
        "nbls": header.get("nbls"),
        "ntimes": header.get("ntimes"),
        "nfreqs": header.get("nfreqs"),
        "npols": header.get("npols"),
        "vis_units": header.get("vis_units"),
        "byte_size": header.get("byte_size"),
        "history_tail": (header.get("history") or "")[-500:],
    }

    missing = [
        field_name
        for field_name in _REQUIRED_METADATA_FIELDS
        if header.get(field_name) is None
    ]
    if missing:
        return CheckResult(
            check_id="metadata_summary",
            status=CheckStatus.FAIL,
            message=(
                "header is missing required field(s): " + ", ".join(missing)
            ),
            details=details,
        )

    return CheckResult(
        check_id="metadata_summary",
        status=CheckStatus.PASS,
        message="all expected header fields are present",
        details=details,
    )


@register_check("beam_type_consistency", CheckTier.FAST)
def check_beam_type_consistency(ctx: CheckContext) -> CheckResult:
    """Does this file's own name agree with the beam type declared by
    the telescope config its recorded history cites?

    This compares two pieces of recorded metadata (the filename and the
    history-cited config's declared beam type) for consistency. It is a
    provenance-consistency check, not proof of what the file's data
    actually contain: the history string may itself be inaccurate or
    stale, and a config file located by name in the search directories
    may not be byte-identical to whatever was in effect at simulation
    time. Agreement between the two is useful supporting evidence, not
    a guarantee; disagreement is a strong, actionable signal to
    investigate before using the file.
    """

    history = ctx.header.get("history") or ""
    cited = find_cited_telescope_configs(history)
    claimed = path_claimed_beam_types(ctx.path)

    if len(claimed) > 1:
        return CheckResult(
            check_id="beam_type_consistency",
            status=CheckStatus.FAIL,
            message=(
                f"file name claims multiple distinct beam types "
                f"{sorted(claimed)}, which is internally inconsistent"
            ),
            details={"path_claimed_beam_types": sorted(claimed)},
        )

    if not cited:
        return CheckResult(
            check_id="beam_type_consistency",
            status=CheckStatus.SKIP,
            message="no telescope_config reference found in history",
            details={"path_claimed_beam_types": sorted(claimed)},
        )

    resolved: dict[str, str | None] = {}
    located: dict[str, str] = {}
    for filename in cited:
        config_path = locate_config(filename, ctx.config_search_dirs)
        if config_path is None:
            resolved[filename] = None
            continue
        located[filename] = str(config_path)
        resolved[filename] = declared_beam_type(config_path)

    unresolved = [name for name, label in resolved.items() if label is None]
    resolved_labels = {
        label for label in resolved.values() if label is not None
    }

    details = {
        "cited_configs": cited,
        "located_configs": located,
        "declared_beam_types": resolved,
        "path_claimed_beam_types": sorted(claimed),
    }

    if not resolved_labels:
        return CheckResult(
            check_id="beam_type_consistency",
            status=CheckStatus.WARN,
            message=(
                "history cites telescope config(s) "
                f"{cited} but none could be located/parsed in the "
                "configured search directories; declared beam type "
                "unknown"
            ),
            details=details,
        )

    if len(resolved_labels) > 1:
        return CheckResult(
            check_id="beam_type_consistency",
            status=CheckStatus.WARN,
            message=(
                "history cites telescope configs with conflicting "
                f"declared beam types: {resolved}"
            ),
            details=details,
        )

    declared = next(iter(resolved_labels))

    if claimed and declared not in claimed:
        return CheckResult(
            check_id="beam_type_consistency",
            status=CheckStatus.FAIL,
            message=(
                f"file name claims beam type(s) {sorted(claimed)}, but "
                f"its cited telescope config declares '{declared}'"
            ),
            details=details,
        )

    if ctx.expected_beam_type and declared != ctx.expected_beam_type:
        return CheckResult(
            check_id="beam_type_consistency",
            status=CheckStatus.FAIL,
            message=(
                f"cited telescope config declares beam type "
                f"'{declared}', which does not match the expected "
                f"beam type '{ctx.expected_beam_type}'"
            ),
            details=details,
        )

    if unresolved:
        return CheckResult(
            check_id="beam_type_consistency",
            status=CheckStatus.WARN,
            message=(
                f"file name and the located config(s) agree on beam "
                f"type '{declared}', but config(s) {unresolved} cited "
                "in the history could not be located to check as well"
            ),
            details=details,
        )

    return CheckResult(
        check_id="beam_type_consistency",
        status=CheckStatus.PASS,
        message=(
            f"file name and its cited telescope config agree on beam "
            f"type '{declared}'"
        ),
        details=details,
    )
