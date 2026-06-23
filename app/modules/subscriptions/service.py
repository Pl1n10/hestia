"""Subscriptions module - service layer (single source of truth)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.base import ModuleSummary, StatItem, SummaryItem
from app.util import humanize_until

from .models import Subscription

MANIFEST_KEY = "subscriptions"

# Normalisation factors -> monthly cost, kept in Decimal to avoid float drift.
_MONTHLY_FACTOR: dict[str, Decimal] = {
    "weekly": Decimal(52) / Decimal(12),
    "monthly": Decimal(1),
    "quarterly": Decimal(1) / Decimal(3),
    "yearly": Decimal(1) / Decimal(12),
}
_CENTS = Decimal("0.01")


def _dec(value: float | Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value))


class DuplicateSubscriptionError(ValueError):
    """An active subscription with this name already exists for the household.

    Carries the existing row so a surface can point the human/agent at it: the
    right move is to *update* (or delete) that one, not add a second. This is the
    guard that closes the duplicate-Netflix loop documented in FAILURES F-007/F-008.
    """

    def __init__(self, existing: Subscription) -> None:
        self.existing = existing
        super().__init__(
            f"A subscription named {existing.name!r} already exists (id={existing.id})."
        )


def find_active_by_name(
    db: Session, household_id: int, name: str
) -> Subscription | None:
    """Return the active subscription matching ``name`` (case/space-insensitive), if any."""
    target = (name or "").strip().casefold()
    if not target:
        return None
    for sub in list_subscriptions(db, household_id, active_only=True):
        if sub.name.strip().casefold() == target:
            return sub
    return None


# --- CRUD ---------------------------------------------------------------- #
def list_subscriptions(
    db: Session, household_id: int, *, active_only: bool = False
) -> list[Subscription]:
    stmt = select(Subscription).where(Subscription.household_id == household_id)
    if active_only:
        stmt = stmt.where(Subscription.active.is_(True))
    stmt = stmt.order_by(Subscription.name)
    return list(db.execute(stmt).scalars())


def get_subscription(db: Session, household_id: int, sub_id: int) -> Subscription | None:
    sub = db.get(Subscription, sub_id)
    if sub is None or sub.household_id != household_id:
        return None
    return sub


def create_subscription(
    db: Session, household_id: int, *, allow_duplicate: bool = False, **fields
) -> Subscription:
    if not allow_duplicate:
        existing = find_active_by_name(db, household_id, fields.get("name", ""))
        if existing is not None:
            raise DuplicateSubscriptionError(existing)
    fields["amount"] = _dec(fields.get("amount"))
    sub = Subscription(household_id=household_id, **fields)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def update_subscription(
    db: Session, household_id: int, sub_id: int, **changes
) -> Subscription | None:
    sub = get_subscription(db, household_id, sub_id)
    if sub is None:
        return None
    for key, value in changes.items():
        if value is None:
            continue
        if key == "amount":
            value = _dec(value)
        setattr(sub, key, value)
    db.commit()
    db.refresh(sub)
    return sub


def delete_subscription(db: Session, household_id: int, sub_id: int) -> bool:
    sub = get_subscription(db, household_id, sub_id)
    if sub is None:
        return False
    db.delete(sub)
    db.commit()
    return True


# --- analytics ----------------------------------------------------------- #
def monthly_cost(db: Session, household_id: int) -> Decimal:
    total = Decimal("0.00")
    for sub in list_subscriptions(db, household_id, active_only=True):
        factor = _MONTHLY_FACTOR.get(sub.cycle, Decimal(1))
        total += _dec(sub.amount) * factor
    return total.quantize(_CENTS, rounding=ROUND_HALF_UP)


def upcoming(db: Session, household_id: int, *, days: int = 30) -> list[Subscription]:
    horizon = date.today() + timedelta(days=days)
    stmt = (
        select(Subscription)
        .where(
            Subscription.household_id == household_id,
            Subscription.active.is_(True),
            Subscription.next_renewal.is_not(None),
            Subscription.next_renewal <= horizon,
        )
        .order_by(Subscription.next_renewal.asc())
    )
    return list(db.execute(stmt).scalars())


# --- summary (home card) ------------------------------------------------- #
def _severity_for(renewal: date) -> str:
    days = (renewal - date.today()).days
    if days < 0:
        return "danger"
    if days <= 7:
        return "warning"
    return "info"


def summary(db: Session, household_id: int) -> ModuleSummary:
    active = list_subscriptions(db, household_id, active_only=True)
    monthly = monthly_cost(db, household_id)
    yearly = (monthly * 12).quantize(_CENTS)
    soon = upcoming(db, household_id, days=30)

    if not active:
        headline = "Nessuna subscription attiva"
    elif soon:
        nxt = soon[0]
        headline = f"€{monthly}/mese · prossimo: {nxt.name} {humanize_until(nxt.next_renewal)}"
    else:
        headline = f"€{monthly}/mese · nessun rinnovo nei prossimi 30g"

    # Card preview lists *every* active subscription, soonest renewal first and
    # undated ones last, so a far-future plan (e.g. a yearly Amazon Prime) still
    # shows up instead of being hidden behind the 30-day `upcoming` window.
    ordered = sorted(
        active, key=lambda s: (s.next_renewal is None, s.next_renewal or date.max)
    )
    items = [
        SummaryItem(
            title=f"{s.name} · €{s.amount}",
            subtitle=s.category,
            when=humanize_until(s.next_renewal) if s.next_renewal else None,
            severity=_severity_for(s.next_renewal) if s.next_renewal else "normal",
        )
        for s in ordered
    ]

    return ModuleSummary(
        key=MANIFEST_KEY,
        name="Subscription",
        icon="💳",
        headline=headline,
        stats=[
            StatItem(label="Attive", value=str(len(active))),
            StatItem(label="€/mese", value=f"{monthly}"),
            StatItem(label="€/anno", value=f"{yearly}"),
        ],
        items=items,
    )
