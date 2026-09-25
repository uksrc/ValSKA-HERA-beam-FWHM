"""Utility helpers for external tools."""

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """Return a UTC timestamp suitable for directory naming."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
