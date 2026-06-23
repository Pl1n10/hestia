"""Register the built-in integrations (stubs are safe to import)."""

from app.integrations.base import (
    Integration,
    IntegrationManifest,
    get_integration,
    get_registry,
    register,
)
from app.integrations.bring import Bring
from app.integrations.gmail import Gmail
from app.integrations.google_calendar import GoogleCalendar

register(GoogleCalendar())
register(Gmail())
register(Bring())

__all__ = [
    "Integration",
    "IntegrationManifest",
    "register",
    "get_registry",
    "get_integration",
]
