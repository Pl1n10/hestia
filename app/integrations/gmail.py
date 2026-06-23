"""Gmail integration (STUB).

Intended use: surface *important* mail (bills, renewals) so Hermes can turn
them into subscriptions/utilities entries. Wiring plan mirrors Calendar:
OAuth2 + Gmail API users.messages.list with a query (e.g. label:important).
"""

from __future__ import annotations

from app.integrations.base import Integration, IntegrationManifest, MailSummary


class Gmail(Integration):
    manifest = IntegrationManifest(
        key="gmail",
        name="Gmail",
        kind="mail",
        description="Email importanti (bollette, rinnovi) da inoltrare ai moduli.",
        requires=["google_client_id", "google_client_secret"],
    )

    def sync(self) -> dict:
        raise NotImplementedError("Google OAuth wiring pending.")

    def list_important(self, *, limit: int = 20) -> list[MailSummary]:  # MailSource
        raise NotImplementedError("Google OAuth wiring pending.")
