"""Vehicles module — bollo, assicurazione, tagliandi.

Tests cover: service CRUD, money exactness (D-007/F-001), upcoming window,
summary card coherence (F-007), full MCP write surface (F-008), REST routes.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.modules.vehicles import service


# --- helpers ---------------------------------------------------------------- #

def _car(db, name="Fiat 500", **kw) -> object:
    return service.create_vehicle(db, 1, name=name, **kw)


def _expense(db, vehicle_id, category="tagliando", **kw) -> object:
    kw.setdefault("amount", 0)
    return service.create_expense(db, 1, vehicle_id, category=category, **kw)


# --- vehicle CRUD ----------------------------------------------------------- #

def test_create_and_list_vehicle(db):
    _car(db)
    vehicles = service.list_vehicles(db, 1)
    assert len(vehicles) == 1
    assert vehicles[0].name == "Fiat 500"


def test_active_only_filter(db):
    _car(db, name="Attiva")
    _car(db, name="Dismessa", active=False)
    active = service.list_vehicles(db, 1, active_only=True)
    assert [v.name for v in active] == ["Attiva"]


def test_vehicle_household_scoping(db):
    service.create_vehicle(db, 1, name="Mia")
    service.create_vehicle(db, 2, name="Altrui")
    assert [v.name for v in service.list_vehicles(db, 1)] == ["Mia"]


def test_update_vehicle(db):
    v = _car(db)
    service.update_vehicle(db, 1, v.id, plate="AB123CD")
    assert service.get_vehicle(db, 1, v.id).plate == "AB123CD"


def test_delete_vehicle(db):
    v = _car(db)
    assert service.delete_vehicle(db, 1, v.id) is True
    assert service.get_vehicle(db, 1, v.id) is None


def test_get_vehicle_wrong_household_returns_none(db):
    v = _car(db)
    assert service.get_vehicle(db, 99, v.id) is None


# --- expense CRUD ----------------------------------------------------------- #

def test_create_and_list_expense(db):
    v = _car(db)
    _expense(db, v.id, category="bollo", amount=150.50,
             due_date=date.today() + timedelta(days=30))
    exps = service.list_expenses(db, 1, vehicle_id=v.id)
    assert len(exps) == 1
    assert exps[0].category == "bollo"


def test_expense_household_scoping(db):
    v1 = service.create_vehicle(db, 1, name="Mia")
    v2 = service.create_vehicle(db, 2, name="Altrui")
    service.create_expense(db, 1, v1.id, category="tagliando", amount=0)
    service.create_expense(db, 2, v2.id, category="tagliando", amount=0)
    assert len(service.list_expenses(db, 1)) == 1
    assert len(service.list_expenses(db, 2)) == 1


def test_update_expense(db):
    v = _car(db)
    exp = _expense(db, v.id, category="bollo", amount=100)
    service.update_expense(db, 1, exp.id, amount=120, paid_date=date.today())
    updated = service.get_expense(db, 1, exp.id)
    assert updated.amount == Decimal("120.00")
    assert updated.paid_date == date.today()


def test_delete_expense(db):
    v = _car(db)
    exp = _expense(db, v.id)
    assert service.delete_expense(db, 1, exp.id) is True
    assert service.get_expense(db, 1, exp.id) is None


def test_delete_vehicle_cascades_to_expenses(db):
    v = _car(db)
    exp = _expense(db, v.id, due_date=date.today() + timedelta(days=10))
    service.delete_vehicle(db, 1, v.id)
    assert service.get_expense(db, 1, exp.id) is None


# --- money precision (D-007 / F-001) --------------------------------------- #

def test_amount_is_decimal_in_db_float_on_surface(db):
    from app.modules.vehicles.schemas import ExpenseOut

    v = _car(db)
    exp = _expense(db, v.id, amount=299.99)
    assert isinstance(exp.amount, Decimal)
    out = ExpenseOut.model_validate(exp)
    assert isinstance(out.amount, float)
    assert out.amount == 299.99


def test_total_pending_cost_is_exact(db):
    v = _car(db)
    today = date.today()
    _expense(db, v.id, amount=150.50, due_date=today + timedelta(days=5))
    _expense(db, v.id, amount=300.00, due_date=today + timedelta(days=10))
    _expense(db, v.id, amount=50.00, due_date=today + timedelta(days=1), paid_date=today)
    cost = service.total_pending_cost(db, 1)
    assert cost == Decimal("450.50")


# --- upcoming / pending ----------------------------------------------------- #

def test_upcoming_includes_overdue_excludes_paid(db):
    v = _car(db)
    today = date.today()
    _expense(db, v.id, category="bollo", due_date=today - timedelta(days=3))       # overdue
    _expense(db, v.id, category="assicurazione", due_date=today + timedelta(days=5))  # upcoming
    _expense(db, v.id, category="tagliando", due_date=today + timedelta(days=60))   # too far
    _expense(db, v.id, category="tagliando", due_date=today + timedelta(days=10),
             paid_date=today)                                                         # paid → excluded
    rows = service.upcoming_expenses(db, 1, days=30)
    cats = [r.category for r in rows]
    assert "bollo" in cats
    assert "assicurazione" in cats
    assert "tagliando" not in cats


def test_pending_expenses_excludes_paid(db):
    v = _car(db)
    today = date.today()
    _expense(db, v.id, due_date=today + timedelta(days=10))
    _expense(db, v.id, due_date=today + timedelta(days=5), paid_date=today)
    pending = service.pending_expenses(db, 1)
    assert len(pending) == 1


def test_upcoming_sorted_by_due_date(db):
    v = _car(db)
    today = date.today()
    _expense(db, v.id, category="tagliando", due_date=today + timedelta(days=20))
    _expense(db, v.id, category="bollo", due_date=today + timedelta(days=5))
    rows = service.upcoming_expenses(db, 1, days=30)
    assert rows[0].category == "bollo"


# --- severity --------------------------------------------------------------- #

def test_severity_buckets(db):
    today = date.today()
    assert service._severity_for(today - timedelta(days=1)) == "danger"
    assert service._severity_for(today + timedelta(days=10)) == "warning"
    assert service._severity_for(today + timedelta(days=30)) == "info"


# --- summary card coherence (F-007) ---------------------------------------- #

def test_summary_empty_state(db):
    s = service.summary(db, 1)
    assert "Nessun veicolo" in s.headline
    assert s.items == []


def test_summary_no_pending_expenses(db):
    _car(db)
    s = service.summary(db, 1)
    assert "nessuna scadenza pendente" in s.headline
    assert s.items == []


def test_summary_items_match_pending_stat(db):
    """Items and 'Scadenze' stat must count the same set (F-007)."""
    v = _car(db)
    today = date.today()
    _expense(db, v.id, category="bollo", due_date=today + timedelta(days=5))
    _expense(db, v.id, category="assicurazione", due_date=today + timedelta(days=90))
    _expense(db, v.id, category="tagliando", due_date=today - timedelta(days=2))
    # paid expense must not appear
    _expense(db, v.id, category="tagliando", due_date=today + timedelta(days=1),
             paid_date=today)

    s = service.summary(db, 1)
    scadenze_stat = next(st for st in s.stats if st.label == "Scadenze")
    assert int(scadenze_stat.value) == len(s.items)
    assert int(scadenze_stat.value) == 3  # bollo + assicurazione + overdue tagliando


def test_summary_headline_shows_next_deadline(db):
    v = _car(db, name="Panda")
    today = date.today()
    _expense(db, v.id, category="bollo", due_date=today + timedelta(days=3))
    s = service.summary(db, 1)
    assert "Bollo" in s.headline
    assert "Panda" in s.headline


# --- MCP surface (F-008 parity) -------------------------------------------- #

def test_mcp_add_and_list_vehicle(db):
    from app.modules.vehicles import mcp

    res = mcp.vehicles_add("Panda", plate="XY999ZZ", make="Fiat")
    assert res["name"] == "Panda"
    assert res["plate"] == "XY999ZZ"
    rows = mcp.vehicles_list(active_only=False)
    assert len(rows) == 1


def test_mcp_update_vehicle_no_duplicate(db):
    from app.modules.vehicles import mcp

    res = mcp.vehicles_add("Fiat 500")
    vid = res["id"]
    mcp.vehicles_update(vid, plate="AA000BB")
    rows = mcp.vehicles_list(active_only=False)
    assert len(rows) == 1
    assert rows[0]["plate"] == "AA000BB"


def test_mcp_delete_vehicle(db):
    from app.modules.vehicles import mcp

    res = mcp.vehicles_add("Da cancellare")
    mcp.vehicles_delete(res["id"])
    assert mcp.vehicles_list(active_only=False) == []
    assert "error" in mcp.vehicles_delete(res["id"])


def test_mcp_expense_add_update_delete(db):
    from app.modules.vehicles import mcp

    v = mcp.vehicles_add("Punto")
    vid = v["id"]

    exp = mcp.vehicles_expense_add(vid, "bollo", due_date="2027-03-31", amount=155.00)
    assert exp["category"] == "bollo"
    assert exp["amount"] == 155.00

    updated = mcp.vehicles_expense_update(exp["id"], paid_date="2027-03-20")
    assert updated["paid_date"] == "2027-03-20"

    assert mcp.vehicles_expense_delete(exp["id"]) == {"deleted": True, "id": exp["id"]}
    assert "error" in mcp.vehicles_expense_delete(exp["id"])


def test_mcp_upcoming(db):
    from app.modules.vehicles import mcp

    v = mcp.vehicles_add("Bravo")
    today = date.today()
    mcp.vehicles_expense_add(v["id"], "assicurazione",
                              due_date=(today + timedelta(days=10)).isoformat(), amount=400)
    mcp.vehicles_expense_add(v["id"], "bollo",
                              due_date=(today + timedelta(days=60)).isoformat(), amount=200)
    rows = mcp.vehicles_upcoming(days=30)
    assert len(rows) == 1
    assert rows[0]["category"] == "assicurazione"


def test_mcp_unknown_vehicle_returns_error(db):
    from app.modules.vehicles import mcp

    assert "error" in mcp.vehicles_update(9999, name="Ghost")
    assert "error" in mcp.vehicles_delete(9999)


def test_mcp_unknown_expense_returns_error(db):
    from app.modules.vehicles import mcp

    assert "error" in mcp.vehicles_expense_update(9999, amount=1.0)
    assert "error" in mcp.vehicles_expense_delete(9999)


# --- REST ------------------------------------------------------------------- #

def test_rest_crud_vehicle(client):
    r = client.post(
        "/api/modules/vehicles/vehicles",
        json={"name": "Golf", "plate": "GF001GF", "make": "Volkswagen"},
    )
    assert r.status_code == 201
    vid = r.json()["id"]

    r = client.get("/api/modules/vehicles/vehicles")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.patch(f"/api/modules/vehicles/vehicles/{vid}", json={"year": 2020})
    assert r.status_code == 200
    assert r.json()["year"] == 2020

    r = client.delete(f"/api/modules/vehicles/vehicles/{vid}")
    assert r.status_code == 204


def test_rest_expense_lifecycle(client):
    r = client.post("/api/modules/vehicles/vehicles", json={"name": "Punto"})
    vid = r.json()["id"]

    r = client.post(
        f"/api/modules/vehicles/vehicles/{vid}/expenses",
        json={"category": "bollo", "amount": 155.0, "due_date": "2027-03-31"},
    )
    assert r.status_code == 201
    eid = r.json()["id"]

    r = client.get(f"/api/modules/vehicles/vehicles/{vid}/expenses")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.patch(
        f"/api/modules/vehicles/vehicles/{vid}/expenses/{eid}",
        json={"paid_date": "2027-03-20"},
    )
    assert r.status_code == 200
    assert r.json()["paid_date"] == "2027-03-20"

    r = client.delete(f"/api/modules/vehicles/vehicles/{vid}/expenses/{eid}")
    assert r.status_code == 204


def test_rest_upcoming(client):
    today = date.today()
    r = client.post("/api/modules/vehicles/vehicles", json={"name": "Ypsilon"})
    vid = r.json()["id"]
    client.post(
        f"/api/modules/vehicles/vehicles/{vid}/expenses",
        json={"category": "assicurazione", "amount": 500.0,
              "due_date": (today + timedelta(days=10)).isoformat()},
    )
    r = client.get("/api/modules/vehicles/vehicles/upcoming?days=30")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_rest_404_on_missing_vehicle(client):
    r = client.get("/api/modules/vehicles/vehicles/9999")
    assert r.status_code == 404
