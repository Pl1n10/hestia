"""Vehicles module - MCP tools.

Full write parity with REST: list, add, update, delete for both vehicles
and expenses. Prevents the agent from being left with an add-only surface
that forces duplicates (FAILURES F-008 / ANTIPATTERNS surface capability drift).
"""

from __future__ import annotations

from dateutil import parser as dtparser

from app.db import SessionLocal
from app.modules.base import McpTool
from app.settings import settings

from . import service
from .models import EXPENSE_CATEGORIES
from .schemas import ExpenseOut, VehicleOut


def _hh() -> int:
    return settings.default_household_id


# --- vehicles --------------------------------------------------------------- #

def vehicles_list(active_only: bool = True) -> list[dict]:
    """List vehicles (active only by default)."""
    with SessionLocal() as db:
        rows = service.list_vehicles(db, _hh(), active_only=active_only)
        return [VehicleOut.model_validate(r).model_dump(mode="json") for r in rows]


def vehicles_add(
    name: str,
    plate: str | None = None,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    notes: str | None = None,
) -> dict:
    """Register a vehicle.

    Args:
        name: display name (e.g. "Fiat 500").
        plate: licence plate (e.g. "AB123CD").
        make: manufacturer (e.g. "Fiat").
        model: model name (e.g. "500").
        year: year of registration.
        notes: optional free text.
    """
    with SessionLocal() as db:
        v = service.create_vehicle(
            db, _hh(), name=name, plate=plate, make=make, model=model, year=year, notes=notes
        )
        return VehicleOut.model_validate(v).model_dump(mode="json")


def vehicles_update(
    vehicle_id: int,
    name: str | None = None,
    plate: str | None = None,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    active: bool | None = None,
    notes: str | None = None,
) -> dict:
    """Edit an existing vehicle (only the fields you pass change).

    Args:
        vehicle_id: the vehicle id (from vehicles_list).
        name: new display name.
        plate: new licence plate.
        make: new manufacturer.
        model: new model name.
        year: new registration year.
        active: set False to deactivate the vehicle.
        notes: free text.
    """
    changes: dict = {}
    for key, value in (
        ("name", name),
        ("plate", plate),
        ("make", make),
        ("model", model),
        ("year", year),
        ("active", active),
        ("notes", notes),
    ):
        if value is not None:
            changes[key] = value
    with SessionLocal() as db:
        v = service.update_vehicle(db, _hh(), vehicle_id, **changes)
        if v is None:
            return {"error": f"No vehicle with id {vehicle_id}."}
        return VehicleOut.model_validate(v).model_dump(mode="json")


def vehicles_delete(vehicle_id: int) -> dict:
    """Delete a vehicle and all its expenses (e.g. a duplicate)."""
    with SessionLocal() as db:
        ok = service.delete_vehicle(db, _hh(), vehicle_id)
        if not ok:
            return {"error": f"No vehicle with id {vehicle_id}."}
        return {"deleted": True, "id": vehicle_id}


# --- expenses --------------------------------------------------------------- #

def vehicles_expense_list(vehicle_id: int | None = None) -> list[dict]:
    """List expenses/deadlines, optionally filtered to one vehicle."""
    with SessionLocal() as db:
        rows = service.list_expenses(db, _hh(), vehicle_id=vehicle_id)
        return [ExpenseOut.model_validate(r).model_dump(mode="json") for r in rows]


def vehicles_expense_add(
    vehicle_id: int,
    category: str,
    due_date: str | None = None,
    amount: float = 0.0,
    currency: str = "EUR",
    paid_date: str | None = None,
    notes: str | None = None,
) -> dict:
    """Add an expense or deadline to a vehicle.

    Args:
        vehicle_id: the vehicle id (from vehicles_list).
        category: bollo | assicurazione | tagliando.
        due_date: ISO date (YYYY-MM-DD) when the expense is due.
        amount: cost in the given currency.
        currency: ISO currency code, default EUR.
        paid_date: ISO date when it was paid (omit if not yet paid).
        notes: optional free text.
    """
    cat = category if category in EXPENSE_CATEGORIES else "tagliando"
    with SessionLocal() as db:
        exp = service.create_expense(
            db,
            _hh(),
            vehicle_id,
            category=cat,
            amount=amount,
            currency=currency,
            due_date=dtparser.isoparse(due_date).date() if due_date else None,
            paid_date=dtparser.isoparse(paid_date).date() if paid_date else None,
            notes=notes,
        )
        return ExpenseOut.model_validate(exp).model_dump(mode="json")


def vehicles_expense_update(
    expense_id: int,
    category: str | None = None,
    due_date: str | None = None,
    amount: float | None = None,
    currency: str | None = None,
    paid_date: str | None = None,
    notes: str | None = None,
) -> dict:
    """Edit an expense in place (only the fields you pass change).

    Use this to record payment (set paid_date) or fix a date/amount.
    Call vehicles_expense_list first to get the expense_id.

    Args:
        expense_id: the expense id (from vehicles_expense_list).
        category: bollo | assicurazione | tagliando.
        due_date: ISO date (YYYY-MM-DD).
        amount: new cost.
        currency: ISO currency code.
        paid_date: ISO date when paid; set to today to mark as paid.
        notes: free text.
    """
    changes: dict = {}
    if category is not None:
        changes["category"] = category if category in EXPENSE_CATEGORIES else "tagliando"
    if amount is not None:
        changes["amount"] = amount
    if currency is not None:
        changes["currency"] = currency
    if due_date is not None:
        changes["due_date"] = dtparser.isoparse(due_date).date()
    if paid_date is not None:
        changes["paid_date"] = dtparser.isoparse(paid_date).date()
    if notes is not None:
        changes["notes"] = notes
    with SessionLocal() as db:
        exp = service.update_expense(db, _hh(), expense_id, **changes)
        if exp is None:
            return {"error": f"No expense with id {expense_id}."}
        return ExpenseOut.model_validate(exp).model_dump(mode="json")


def vehicles_expense_delete(expense_id: int) -> dict:
    """Delete an expense (e.g. a duplicate). Call vehicles_expense_list first."""
    with SessionLocal() as db:
        ok = service.delete_expense(db, _hh(), expense_id)
        if not ok:
            return {"error": f"No expense with id {expense_id}."}
        return {"deleted": True, "id": expense_id}


def vehicles_upcoming(days: int = 30) -> list[dict]:
    """Expenses due within the given number of days (includes overdue, excludes paid)."""
    with SessionLocal() as db:
        rows = service.upcoming_expenses(db, _hh(), days=days)
        return [ExpenseOut.model_validate(r).model_dump(mode="json") for r in rows]


TOOLS = [
    McpTool("vehicles_list", "List registered vehicles.", vehicles_list),
    McpTool("vehicles_add", "Register a new vehicle.", vehicles_add),
    McpTool("vehicles_update", "Edit a vehicle (avoids duplicates).", vehicles_update),
    McpTool("vehicles_delete", "Delete a vehicle and its expenses.", vehicles_delete),
    McpTool("vehicles_expense_list", "List expenses/deadlines for a vehicle.", vehicles_expense_list),
    McpTool("vehicles_expense_add", "Add a bollo / assicurazione / tagliando expense.", vehicles_expense_add),
    McpTool("vehicles_expense_update", "Edit an expense (e.g. record payment).", vehicles_expense_update),
    McpTool("vehicles_expense_delete", "Delete an expense.", vehicles_expense_delete),
    McpTool("vehicles_upcoming", "List expenses due within N days (includes overdue).", vehicles_upcoming),
]
