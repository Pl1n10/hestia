"""Integrations — capability protocols, registry, and stub behaviour."""

from __future__ import annotations

import pytest

from app.integrations.base import Integration, ShoppingList, get_integration, get_registry
from app.integrations.fake import FakeShoppingList


def test_fake_shopping_satisfies_protocol():
    fake = FakeShoppingList()
    assert isinstance(fake, ShoppingList)
    assert fake.is_configured() is True


def test_fake_shopping_round_trip():
    fake = FakeShoppingList()
    fake.add_item("latte")
    fake.add_item("pane")
    fake.add_item("latte")  # dedup
    assert fake.get_items() == ["latte", "pane"]
    fake.remove_item("latte")
    assert fake.get_items() == ["pane"]


def test_registry_contains_the_shipped_integrations():
    import app.integrations  # noqa: F401  (triggers registration)

    reg = get_registry()
    assert {"google_calendar", "gmail", "bring"} <= set(reg)


def test_stub_integrations_are_unconfigured_by_default():
    import app.integrations  # noqa: F401

    gmail = get_integration("gmail")
    assert gmail is not None
    assert gmail.is_configured() is False
    health = gmail.health()
    assert health["configured"] is False


def test_stub_sync_raises_not_implemented():
    import app.integrations  # noqa: F401

    bring = get_integration("bring")
    with pytest.raises(NotImplementedError):
        bring.sync()
