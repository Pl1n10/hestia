"""Bring! integration (STUB).

Bring exposes no official public API. There is a community reverse-engineered
client (`bring-api` on PyPI, used by Home Assistant). Strategy: depend on the
ShoppingList *protocol*, not Bring directly, so we can ship with the local
FakeShoppingList and swap Bring in later — or drop it if the unofficial API
breaks — without touching the shopping module. (See docs/FAILURES.md F-002.)
Requires HESTIA_BRING_EMAIL / HESTIA_BRING_PASSWORD.
"""

from __future__ import annotations

from app.integrations.base import Integration, IntegrationManifest


class Bring(Integration):
    manifest = IntegrationManifest(
        key="bring",
        name="Bring!",
        kind="shopping",
        description="Lista della spesa Bring (API non ufficiale).",
        requires=["bring_email", "bring_password"],
    )

    def sync(self) -> dict:
        raise NotImplementedError("Bring client wiring pending (unofficial API).")

    def get_items(self) -> list[str]:  # ShoppingList
        raise NotImplementedError("Bring client wiring pending.")

    def add_item(self, item: str) -> None:
        raise NotImplementedError("Bring client wiring pending.")

    def remove_item(self, item: str) -> None:
        raise NotImplementedError("Bring client wiring pending.")
