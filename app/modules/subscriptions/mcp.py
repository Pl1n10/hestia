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


def subscriptions_update(
    sub_id: int,
    name: str | None = None,
    amount: float | None = None,
    cycle: str | None = None,
    vendor: str | None = None,
    currency: str | None = None,
    next_renewal: str | None = None,
    category: str | None = None,
    active: bool | None = None,
    notes: str | None = None,
) -> dict:
    """Edit an existing subscription in place (only the fields you pass change).

    Use this instead of adding a second entry when something about a known
    subscription changes — a new price, a new renewal date, or to deactivate it.
    Call ``subscriptions_list`` first to get the ``sub_id``.

    Args:
        sub_id: the subscription id (from subscriptions_list).
        name: new display name.
        amount: new cost per cycle.
        cycle: weekly | monthly | quarterly | yearly.
        vendor: new provider name.
        currency: ISO currency.
        next_renewal: ISO date (YYYY-MM-DD) of the next charge.
        category: new tag.
        active: set False to suspend it (drops it from cost rollups).
        notes: free text.
    """
    changes: dict = {}
    for key, value in (
        ("name", name),
        ("amount", amount),
        ("vendor", vendor),
        ("currency", currency),
        ("category", category),
        ("active", active),
        ("notes", notes),
    ):
        if value is not None:
            changes[key] = value
    if cycle is not None:
        changes["cycle"] = (
            cycle if cycle in ("weekly", "monthly", "quarterly", "yearly") else "monthly"
        )
    if next_renewal is not None:
        changes["next_renewal"] = dtparser.isoparse(next_renewal).date()
    with SessionLocal() as db:
        sub = service.update_subscription(db, _hh(), sub_id, **changes)
        if sub is None:
            return {"error": f"No subscription with id {sub_id}."}
        return SubscriptionOut.model_validate(sub).model_dump(mode="json")


def subscriptions_delete(sub_id: int) -> dict:
    """Delete a subscription for good (e.g. a duplicate). Call subscriptions_list first."""
    with SessionLocal() as db:
        ok = service.delete_subscription(db, _hh(), sub_id)
        if not ok:
            return {"error": f"No subscription with id {sub_id}."}
        return {"deleted": True, "id": sub_id}


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
    McpTool("subscriptions_update", "Edit an existing subscription (avoids duplicates).", subscriptions_update),
    McpTool("subscriptions_delete", "Delete a subscription (e.g. a duplicate).", subscriptions_delete),
    McpTool("subscriptions_monthly_cost", "Get total monthly/yearly subscription spend.", subscriptions_monthly_cost),
    McpTool("subscriptions_upcoming", "List subscriptions renewing soon.", subscriptions_upcoming),
]
