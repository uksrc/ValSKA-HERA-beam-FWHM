"""Small helpers for terminal-oriented CLI formatting."""

from __future__ import annotations

import os
import sys
from typing import Literal, TextIO

from rich.console import Console
from rich.text import Text

ColorMode = Literal["auto", "always", "never"]

_STYLES = {
    "bold_cyan": "bold cyan",
    "dim": "dim",
    "green": "green",
    "yellow": "yellow",
}


class CliColors:
    """Apply Rich terminal styles when color is enabled for a stream."""

    def __init__(
        self,
        mode: ColorMode = "auto",
        *,
        stream: TextIO | None = None,
        enabled: bool = True,
    ) -> None:
        self.mode = mode
        self.stream = stream if stream is not None else sys.stdout
        self.enabled = enabled and self._should_enable()
        self.console = Console(
            force_terminal=self.enabled,
            color_system="standard" if self.enabled else None,
            no_color=not self.enabled,
            file=self.stream,
        )

    def _should_enable(self) -> bool:
        if self.mode == "never":
            return False
        if os.environ.get("NO_COLOR") is not None:
            return False
        if self.mode == "always":
            return True
        return bool(getattr(self.stream, "isatty", lambda: False)())

    def style(self, text: object, style_name: str) -> str:
        value = str(text)
        if not self.enabled:
            return value
        rich_style = _STYLES.get(style_name)
        if rich_style is None:
            return value
        styled = Text(value, style=rich_style)
        with self.console.capture() as capture:
            self.console.print(styled, end="")
        return capture.get()

    def heading(self, text: object) -> str:
        return self.style(text, "bold_cyan")

    def path(self, text: object) -> str:
        return self.style(text, "green")

    def source(self, text: object) -> str:
        return self.style(f"[{text}]", "dim")

    def success(self, text: object) -> str:
        return self.style(text, "green")

    def warning(self, text: object) -> str:
        return self.style(text, "yellow")
