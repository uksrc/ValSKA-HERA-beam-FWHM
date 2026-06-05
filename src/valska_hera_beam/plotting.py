"""Compatibility wrapper for deprecated module `valska_hera_beam.plotting`."""

from __future__ import annotations

from valska_hera_beam._compat import warn_import as _warn_import

_warn_import(__name__, "valska.plotting")

from valska.plotting import *  # noqa: F401,F403
