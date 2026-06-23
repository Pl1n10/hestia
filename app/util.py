"""Small shared helpers. Kept dependency-light on purpose."""

from __future__ import annotations

from datetime import date, datetime, timezone


def ensure_aware(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC (SQLite round-trips can drop tzinfo)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def humanize_ago(dt: datetime, *, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    delta = now - ensure_aware(dt)
    secs = int(delta.total_seconds())
    if secs < 90:
        return "poco fa"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m fa"
    hours = mins // 60
    if hours < 24:
        return f"{hours}h fa"
    days = hours // 24
    if days == 1:
        return "ieri"
    return f"{days}g fa"


def humanize_until(when: date | datetime, *, today: date | None = None) -> str:
    today = today or date.today()
    target = when.date() if isinstance(when, datetime) else when
    days = (target - today).days
    if days < 0:
        n = abs(days)
        return "scaduto ieri" if n == 1 else f"scaduto da {n}g"
    if days == 0:
        return "oggi"
    if days == 1:
        return "domani"
    return f"tra {days}g"
