"""Vehicles module - service layer (single source of truth).

Tracks bollo, assicurazione and tagliandi per vehicle. All money is stored
as Numeric(10,2) and computed with Decimal (DECISIONS D-007 / FAILURES F-001).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.base import ModuleSummary, StatItem, SummaryItem
from app.util import humanize_until

from .models import Vehicle, VehicleExpense

MANIFEST_KEY = "vehicles"

_CENTS = Decimal("0.01")

CATEGORY_LABELS = {
    "bollo": "Bollo",
    "assicurazione": "Assicurazione",
    "tagliando": "Tagliando",
}


def _dec(value: float | Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value))


# --- vehicle CRUD --------------------------------------------------------- #

def list_vehicles(
    db: Session, household_id: int, *, active_only: bool = False
) -> list[Vehicle]:
    stmt = select(Vehicle).where(Vehicle.household_id == household_id)
    if active_only:
        stmt = stmt.where(Vehicle.active.is_(True))
    stmt = stmt.order_by(Vehicle.name)
    return list(db.execute(stmt).scalars())


def get_vehicle(db: Session, household_id: int, vehicle_id: int) -> Vehicle | None:
    v = db.get(Vehicle, vehicle_id)
    if v is None or v.household_id != household_id:
        return None
    return v


def create_vehicle(db: Session, household_id: int, **fields) -> Vehicle:
    v = Vehicle(household_id=household_id, **fields)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def update_vehicle(
    db: Session, household_id: int, vehicle_id: int, **changes
) -> Vehicle | None:
    v = get_vehicle(db, household_id, vehicle_id)
    if v is None:
        return None
    for key, value in changes.items():
        if value is None:
            continue
        setattr(v, key, value)
    db.commit()
    db.refresh(v)
    return v


def delete_vehicle(db: Session, household_id: int, vehicle_id: int) -> bool:
    v = get_vehicle(db, household_id, vehicle_id)
    if v is None:
        return False
    db.delete(v)
    db.commit()
    return True


# --- expense CRUD --------------------------------------------------------- #

def list_expenses(
    db: Session,
    household_id: int,
    vehicle_id: int | None = None,
) -> list[VehicleExpense]:
    stmt = select(VehicleExpense).where(VehicleExpense.household_id == household_id)
    if vehicle_id is not None:
        stmt = stmt.where(VehicleExpense.vehicle_id == vehicle_id)
    stmt = stmt.order_by(VehicleExpense.due_date.asc().nullslast())
    return list(db.execute(stmt).scalars())


def get_expense(db: Session, household_id: int, expense_id: int) -> VehicleExpense | None:
    exp = db.get(VehicleExpense, expense_id)
    if exp is None or exp.household_id != household_id:
        return None
    return exp


def create_expense(
    db: Session, household_id: int, vehicle_id: int, **fields
) -> VehicleExpense:
    fields["amount"] = _dec(fields.get("amount"))
    exp = VehicleExpense(household_id=household_id, vehicle_id=vehicle_id, **fields)
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def update_expense(
    db: Session, household_id: int, expense_id: int, **changes
) -> VehicleExpense | None:
    exp = get_expense(db, household_id, expense_id)
    if exp is None:
        return None
    for key, value in changes.items():
        if value is None:
            continue
        if key == "amount":
            value = _dec(value)
        setattr(exp, key, value)
    db.commit()
    db.refresh(exp)
    return exp


def delete_expense(db: Session, household_id: int, expense_id: int) -> bool:
    exp = get_expense(db, household_id, expense_id)
    if exp is None:
        return False
    db.delete(exp)
    db.commit()
    return True


# --- analytics ------------------------------------------------------------ #

def upcoming_expenses(
    db: Session, household_id: int, *, days: int = 30
) -> list[VehicleExpense]:
    """Unpaid expenses with due_date <= today + days (includes overdue)."""
    horizon = date.today() + timedelta(days=days)
    stmt = (
        select(VehicleExpense)
        .where(
            VehicleExpense.household_id == household_id,
            VehicleExpense.paid_date.is_(None),
            VehicleExpense.due_date.is_not(None),
            VehicleExpense.due_date <= horizon,
        )
        .order_by(VehicleExpense.due_date.asc())
    )
    return list(db.execute(stmt).scalars())


def pending_expenses(db: Session, household_id: int) -> list[VehicleExpense]:
    """All unpaid expenses with a due_date, sorted soonest first."""
    stmt = (
        select(VehicleExpense)
        .where(
            VehicleExpense.household_id == household_id,
            VehicleExpense.paid_date.is_(None),
            VehicleExpense.due_date.is_not(None),
        )
        .order_by(VehicleExpense.due_date.asc())
    )
    return list(db.execute(stmt).scalars())


def total_pending_cost(db: Session, household_id: int) -> Decimal:
    total = Decimal("0.00")
    for exp in pending_expenses(db, household_id):
        total += _dec(exp.amount)
    return total.quantize(_CENTS, rounding=ROUND_HALF_UP)


# --- summary (home card) -------------------------------------------------- #

def _severity_for(due: date) -> str:
    days = (due - date.today()).days
    if days < 0:
        return "danger"
    if days <= 14:
        return "warning"
    return "info"


def summary(db: Session, household_id: int) -> ModuleSummary:
    active = list_vehicles(db, household_id, active_only=True)
    pending = pending_expenses(db, household_id)
    cost = total_pending_cost(db, household_id)

    if not active:
        headline = "Nessun veicolo registrato"
    elif not pending:
        headline = f"{len(active)} veicolo/i · nessuna scadenza pendente"
    else:
        nxt = pending[0]
        v = db.get(Vehicle, nxt.vehicle_id)
        v_name = v.name if v else "?"
        label = CATEGORY_LABELS.get(nxt.category, nxt.category)
        headline = (
            f"{len(active)} veicolo/i · prossima: {label} {v_name}"
            f" {humanize_until(nxt.due_date)}"
        )

    # Items = ALL pending expenses (same set the stats count — ANTIPATTERNS F-007)
    items = []
    for exp in pending:
        v = db.get(Vehicle, exp.vehicle_id)
        v_name = v.name if v else "?"
        label = CATEGORY_LABELS.get(exp.category, exp.category)
        items.append(
            SummaryItem(
                title=f"{label} · {v_name}",
                subtitle=f"€{exp.amount}" if exp.amount else None,
                when=humanize_until(exp.due_date),
                severity=_severity_for(exp.due_date),
            )
        )

    return ModuleSummary(
        key=MANIFEST_KEY,
        name="Veicoli",
        icon="🚗",
        headline=headline,
        stats=[
            StatItem(label="Veicoli", value=str(len(active))),
            StatItem(label="Scadenze", value=str(len(pending))),
            StatItem(label="Costo sospeso", value=f"€{cost}"),
        ],
        items=items,
    )
