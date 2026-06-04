"""Compatibility wrapper for deprecated module `valska_hera_beam.__init__`."""

from __future__ import annotations

from valska_hera_beam._compat import warn_import as _warn_import

_warn_import(__name__, "valska")

from valska import *  # noqa: F401,F403
