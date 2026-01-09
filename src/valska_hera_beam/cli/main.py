from __future__ import annotations

import argparse
from typing import Sequence

from rich.console import Console

from .. import __version__
from .doctor import run_doctor

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valska-beam-validate",
        description=(
            "ValSKA-HERA-beam-FWHM: validation utilities for assessing sensitivity of "
            "21-cm power spectrum forward-modelling pipelines to primary beam FWHM uncertainties."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the installed package version and exit.",
    )

    # Keep room for future subcommands without committing now.
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable more verbose logging output.",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "doctor",
        help="Check whether the environment is ready for ValSKA / BayesEoR workflows.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return run_doctor()

    console.print(
        "[bold]ValSKA-HERA-beam-FWHM[/bold] is installed and ready.\n"
        "Use the notebooks for full validation workflows, or extend this CLI with subcommands.",
        highlight=False,
    )
    return 0
