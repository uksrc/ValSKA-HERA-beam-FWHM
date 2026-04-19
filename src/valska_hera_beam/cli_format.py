"""Small helpers for terminal-oriented CLI formatting."""

from __future__ import annotations

import os
import sys
from typing import Literal, TextIO

ColorMode = Literal["auto", "always", "never"]

_STYLES = {
    "bold_cyan": "\033[1;36m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "yellow": "\033[33m",
}
_RESET = "\033[0m"


class CliColors:
    """Apply ANSI styles when color is enabled for a terminal stream."""

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
        prefix = _STYLES.get(style_name)
        if prefix is None:
            return value
        return f"{prefix}{value}{_RESET}"

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
