"""In-memory integrations for tests + offline demo (no credentials needed)."""

from __future__ import annotations

from app.integrations.base import Integration, IntegrationManifest, ShoppingList


class FakeShoppingList(Integration):
    """A ShoppingList you can use before Bring is wired. Also used in tests."""

    manifest = IntegrationManifest(
        key="fake_shopping",
        name="Lista spesa (locale)",
        kind="shopping",
        description="Lista spesa in memoria; placeholder finché Bring non è collegato.",
        requires=[],
    )

    def __init__(self) -> None:
        self._items: list[str] = []

    # Integration
    def is_configured(self) -> bool:
        return True

    def sync(self) -> dict:
        return {"ok": True, "items": len(self._items)}

    # ShoppingList capability
    def get_items(self) -> list[str]:
        return list(self._items)

    def add_item(self, item: str) -> None:
        if item not in self._items:
            self._items.append(item)

    def remove_item(self, item: str) -> None:
        if item in self._items:
            self._items.remove(item)


# sanity: the concrete class satisfies the protocol
assert isinstance(FakeShoppingList(), ShoppingList)
