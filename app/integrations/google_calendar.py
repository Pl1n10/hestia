"""Google Calendar integration (STUB).

Wiring plan: OAuth2 (offline access) -> store refresh token per household ->
Google Calendar API events.list. Implement `list_events` to satisfy the
CalendarSource protocol. Requires HESTIA_GOOGLE_CLIENT_ID / _SECRET.
"""

from __future__ import annotations

from app.integrations.base import CalendarEvent, Integration, IntegrationManifest


class GoogleCalendar(Integration):
    manifest = IntegrationManifest(
        key="google_calendar",
        name="Google Calendar",
        kind="calendar",
        description="Eventi e appuntamenti dal calendario condiviso.",
        requires=["google_client_id", "google_client_secret"],
    )

    def sync(self) -> dict:
        raise NotImplementedError("Google OAuth wiring pending (see docstring).")

    def list_events(self, *, days: int = 7) -> list[CalendarEvent]:  # CalendarSource
        raise NotImplementedError("Google OAuth wiring pending.")
