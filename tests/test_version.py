"""Tests for package version metadata.

These tests validate that the top-level package exposes a usable version string.

Rationale
---------
Downstream tooling (packagers, provenance tracking, notebooks, reporting) often
expects a canonical ``__version__`` attribute on import. This test ensures:

- The attribute exists on the top-level package.
- It is a string.
- It is not empty/whitespace.

Notes
-----
- This intentionally does **not** enforce a specific version format (e.g. PEP 440)
  to avoid adding extra test dependencies. If you want strict validation, you
  can use ``packaging.version.Version`` in a separate test.
"""


def test_version_exposed():
    """The package should expose a non-empty ``__version__`` string."""
    import valska_hera_beam

    assert hasattr(valska_hera_beam, "__version__")
    assert isinstance(valska_hera_beam.__version__, str)
    assert valska_hera_beam.__version__.strip() != ""
