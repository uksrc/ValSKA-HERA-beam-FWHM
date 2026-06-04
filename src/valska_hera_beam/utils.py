"""Compatibility wrapper for deprecated module `valska_hera_beam.utils`."""

from __future__ import annotations

from valska_hera_beam._compat import warn_import as _warn_import

_warn_import(__name__, "valska.utils")

from valska.utils import *  # noqa: F401,F403
