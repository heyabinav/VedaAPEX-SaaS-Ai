"""Timezone helpers."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return a naive UTC datetime without using deprecated utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utcstart_of_day() -> datetime:
    """Return the start of the current UTC day as a naive datetime."""
    return utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
