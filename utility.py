"""General-purpose helper functions for misc bot utilities."""

from __future__ import annotations

from datetime import datetime, timezone


def format_timestamp(dt: datetime, *, include_timezone: bool = False) -> str:
    """Return an ISO-formatted string for the provided datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if include_timezone:
        return dt.isoformat(timespec="seconds")
    return (
        dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    )


def truncate_message(
    message: str, max_length: int = 2000, *, ellipsis: str = "..."
) -> str:
    """Shorten a string to the given length while indicating truncation."""
    if max_length < 0:
        raise ValueError("max_length must be non-negative")
    if len(message) <= max_length:
        return message
    cutoff = max(max_length - len(ellipsis), 0)
    return message[:cutoff] + (ellipsis if cutoff else "")
