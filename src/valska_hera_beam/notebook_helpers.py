"""Compatibility wrapper for deprecated module `valska_hera_beam.notebook_helpers`."""

from __future__ import annotations

from valska_hera_beam._compat import warn_import as _warn_import

_warn_import(__name__, "valska.notebook_helpers")

from valska.notebook_helpers import *  # noqa: F401,F403
