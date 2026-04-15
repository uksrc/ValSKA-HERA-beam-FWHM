from __future__ import annotations

import importlib
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .. import __version__
from ..utils import get_default_path_manager

console = Console()


def _check_import(module: str) -> tuple[bool, str]:
    """Return (ok, message) for a simple import check."""
    try:
        importlib.import_module(module)
        return True, "OK"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _check_pymultinest() -> tuple[bool, str]:
    """Return (ok, message) for pymultinest import, handling common OSError."""
    try:
        import pymultinest  # noqa: F401

        return True, "OK"
    except OSError as e:
        # Typical case: MultiNest library not found
        return False, f"OSError: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def run_doctor() -> int:
    """Run environment checks and return an exit code."""
    console.print("[bold]ValSKA environment check[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")

    failed = False

    # Python
    table.add_row("Python", "OK", sys.version.split()[0])

    # Package version
    table.add_row("valska", "OK", __version__)

    # Core imports
    for mod in ["numpy", "scipy", "pyuvdata"]:
        ok, msg = _check_import(mod)
        failed |= not ok
        table.add_row(f"import {mod}", "OK" if ok else "FAIL", msg)

    # pymultinest (special handling)
    ok, msg = _check_pymultinest()
    failed |= not ok
    table.add_row("pymultinest / MultiNest", "OK" if ok else "FAIL", msg)

    # Path manager sanity
    try:
        pm = get_default_path_manager()
        table.add_row("Path manager", "OK", f"base={Path(pm.base_dir)}")
    except Exception as e:
        failed = True
        table.add_row("Path manager", "FAIL", f"{type(e).__name__}: {e}")

    console.print(table)

    if failed:
        console.print("\n[red]One or more checks failed.[/red]")
        return 1

    console.print("\n[green]Environment looks good.[/green]")
    return 0
