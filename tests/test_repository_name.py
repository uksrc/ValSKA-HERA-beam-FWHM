from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_core_metadata_uses_valska_name():
    files_to_check = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "docs" / "source" / "conf.py",
        REPO_ROOT / "docs" / "source" / "index.rst",
        REPO_ROOT / "src" / "valska_hera_beam" / "__init__.py",
        REPO_ROOT / "src" / "valska_hera_beam" / "cli" / "main.py",
        REPO_ROOT / "src" / "valska_hera_beam" / "cli" / "doctor.py",
    ]

    for path in files_to_check:
        text = path.read_text(encoding="utf-8")
        assert "ValSKA" in text, f"expected ValSKA branding in {path}"

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    index_rst = (
        REPO_ROOT / "docs" / "source" / "index.rst"
    ).read_text(encoding="utf-8")

    assert "# ValSKA" in readme
    assert 'name = "valska"' in pyproject
    assert 'project = "ValSKA"' in (
        REPO_ROOT / "docs" / "source" / "conf.py"
    ).read_text(encoding="utf-8")
    assert "ValSKA documentation" in index_rst
