"""Compatibility wrapper for deprecated module `valska_hera_beam.cli.doctor`."""

from __future__ import annotations

from valska_hera_beam._compat import warn_import as _warn_import

_warn_import(__name__, "valska.cli.doctor")

from valska.cli.doctor import *  # noqa: F401,F403
