"""Subscriptions module - MCP tools.

The intended flow: Hermes reads an invoice/receipt from Gmail, then calls
``subscriptions_add`` to record it. Humans see the same entry in the app.
"""

from __future__ import annotations

from dateutil import parser as dtparser

from app.db import SessionLocal
from app.modules.base import McpTool
from app.settings import settings

from . import service
from .schemas import SubscriptionOut


def _hh() -> int:
    return settings.default_household_id


def subscriptions_list(active_only: bool = True) -> list[dict]:
    """List subscriptions (active only by default)."""
    with SessionLocal() as db:
        rows = service.list_subscriptions(db, _hh(), active_only=active_only)
        return [SubscriptionOut.model_validate(r).model_dump(mode="json") for r in rows]


def subscriptions_add(
    name: str,
    amount: float,
    cycle: str = "monthly",
    vendor: str | None = None,
    currency: str = "EUR",
    next_renewal: str | None = None,
    category: str | None = None,
    notes: str | None = None,
) -> dict:
    """Add a subscription / recurring cost.

    Args:
        name: display name (e.g. "Netflix").
        amount: cost per cycle.
        cycle: weekly | monthly | quarterly | yearly.
        vendor: optional provider name.
        currency: ISO currency, default EUR.
        next_renewal: optional ISO date (YYYY-MM-DD) of the next charge.
        category: optional tag (streaming, software, utenze...).
        notes: optional free text.
    """
    with SessionLocal() as db:
        renewal = dtparser.isoparse(next_renewal).date() if next_renewal else None
        sub = service.create_subscription(
            db,
            _hh(),
            name=name,
            amount=amount,
            cycle=cycle if cycle in ("weekly", "monthly", "quarterly", "yearly") else "monthly",
            vendor=vendor,
            currency=currency,
            next_renewal=renewal,
            category=category,
            notes=notes,
        )
        return SubscriptionOut.model_validate(sub).model_dump(mode="json")


def subscriptions_monthly_cost() -> dict:
    """Total normalised monthly and yearly spend across active subscriptions."""
    with SessionLocal() as db:
        monthly = service.monthly_cost(db, _hh())
        return {"currency": "EUR", "monthly": float(monthly), "yearly": float(monthly * 12)}


def subscriptions_upcoming(days: int = 30) -> list[dict]:
    """Subscriptions renewing within the given number of days (incl. overdue)."""
    with SessionLocal() as db:
        rows = service.upcoming(db, _hh(), days=days)
        return [SubscriptionOut.model_validate(r).model_dump(mode="json") for r in rows]


TOOLS = [
    McpTool("subscriptions_list", "List subscriptions / recurring costs.", subscriptions_list),
    McpTool("subscriptions_add", "Add a subscription or recurring cost.", subscriptions_add),
    McpTool("subscriptions_monthly_cost", "Get total monthly/yearly subscription spend.", subscriptions_monthly_cost),
    McpTool("subscriptions_upcoming", "List subscriptions renewing soon.", subscriptions_upcoming),
]
