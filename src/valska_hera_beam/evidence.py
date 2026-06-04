"""Compatibility wrapper for deprecated module `valska_hera_beam.evidence`."""

from __future__ import annotations

from valska_hera_beam._compat import warn_import as _warn_import

_warn_import(__name__, "valska.evidence")

from valska.evidence import *  # noqa: F401,F403
