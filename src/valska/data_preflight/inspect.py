"""Cheap, header-only inspection of UVH5 files.

Deliberately reads only the ``/Header`` group via h5py rather than a
full ``pyuvdata.UVData.read_uvh5``, so this stays fast enough to run
before every analysis, on files of any size.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py

_SCALAR_INT_FIELDS = (
    "Nants_telescope",
    "Nants_data",
    "Nbls",
    "Ntimes",
    "Nfreqs",
    "Npols",
)
_STRING_FIELDS = ("history", "vis_units")


def _decode(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def read_uvh5_header(path: Path) -> dict[str, Any]:
    """Read key ``/Header`` fields from a UVH5 file without touching data.

    Returns a plain dict with lowercase, snake_case-ish keys (matching
    what the checks in this package expect), plus ``byte_size`` from the
    filesystem.
    """

    path = Path(path)
    result: dict[str, Any] = {"byte_size": path.stat().st_size}

    with h5py.File(path, "r") as handle:
        header = handle["Header"]
        for field_name in _SCALAR_INT_FIELDS:
            if field_name in header:
                result[field_name.lower()] = int(header[field_name][()])
        for field_name in _STRING_FIELDS:
            if field_name in header:
                result[field_name.lower()] = _decode(header[field_name][()])

    return result
