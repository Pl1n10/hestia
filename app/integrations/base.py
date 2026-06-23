"""Integration contracts.

An *integration* is an external data source/sink (Google Calendar, Gmail,
Bring, ...). It declares what config it needs and whether it is currently
configured. Capability *protocols* (CalendarSource, MailSource, ShoppingList)
describe the shape each kind exposes, so modules can depend on the capability
rather than the concrete vendor (swap Bring for a native list without touching
the shopping module).

Only the contracts + stubs live here. Real OAuth/credential wiring is a
follow-up per integration (see docs/STATE.md).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.settings import settings


@dataclass(frozen=True)
class IntegrationManifest:
    key: str
    name: str
    kind: str  # calendar | mail | shopping | ...
    description: str
    requires: list[str] = field(default_factory=list)  # settings attrs needed


class Integration(ABC):
    manifest: IntegrationManifest

    def is_configured(self) -> bool:
        return all(getattr(settings, attr, None) for attr in self.manifest.requires)

    def health(self) -> dict:
        return {
            "key": self.manifest.key,
            "kind": self.manifest.kind,
            "configured": self.is_configured(),
        }

    @abstractmethod
    def sync(self) -> dict:
        """Pull/refresh from the source. Returns a small status dict."""
        raise NotImplementedError


# --- capability protocols ------------------------------------------------ #
@dataclass
class CalendarEvent:
    title: str
    start: datetime
    end: datetime | None = None
    location: str | None = None


@runtime_checkable
class CalendarSource(Protocol):
    def list_events(self, *, days: int = 7) -> list[CalendarEvent]: ...


@dataclass
class MailSummary:
    subject: str
    sender: str
    received_at: datetime
    snippet: str | None = None


@runtime_checkable
class MailSource(Protocol):
    def list_important(self, *, limit: int = 20) -> list[MailSummary]: ...


@runtime_checkable
class ShoppingList(Protocol):
    def get_items(self) -> list[str]: ...
    def add_item(self, item: str) -> None: ...
    def remove_item(self, item: str) -> None: ...


# --- registry ------------------------------------------------------------ #
_REGISTRY: dict[str, Integration] = {}


def register(integration: Integration) -> Integration:
    _REGISTRY[integration.manifest.key] = integration
    return integration


def get_registry() -> dict[str, Integration]:
    return dict(_REGISTRY)


def get_integration(key: str) -> Integration | None:
    return _REGISTRY.get(key)
