"""
ValSKA

Validation tooling for SKA and precursor science workflows, including
21-cm power-spectrum studies of primary beam FWHM uncertainties.
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Version handling
#
# The version is generated at build time by setuptools-scm and written to
# _version.py. When running from a source tree without installation (e.g. on
# HPC systems), this file may not exist, so we fall back gracefully.
# -----------------------------------------------------------------------------

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

__all__ = [
    "__version__",
]
