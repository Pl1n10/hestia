"""Subscriptions module — managed recurring entities with Decimal money math.

The cost rollup is the part most likely to drift, so it gets the most coverage
(docs/FAILURES.md F-001: money is Numeric + Decimal, never float arithmetic).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.modules.subscriptions import service


def _add(db, **kw):
    kw.setdefault("cycle", "monthly")
    return service.create_subscription(db, 1, **kw)


def test_monthly_cost_normalises_each_cycle(db):
    _add(db, name="Mensile", amount=10, cycle="monthly")
    _add(db, name="Annuale", amount=120, cycle="yearly")      # -> 10/mese
    _add(db, name="Trimestrale", amount=30, cycle="quarterly")  # -> 10/mese
    cost = service.monthly_cost(db, 1)
    assert cost == Decimal("30.00")


def test_weekly_rounds_half_up(db):
    _add(db, name="Settimanale", amount=7, cycle="weekly")  # 7 * 52/12 = 30.333...
    assert service.monthly_cost(db, 1) == Decimal("30.33")


def test_inactive_subscriptions_are_excluded_from_cost(db):
    _add(db, name="Attiva", amount=10, cycle="monthly")
    _add(db, name="Sospesa", amount=99, cycle="monthly", active=False)
    assert service.monthly_cost(db, 1) == Decimal("10.00")


def test_amount_is_decimal_in_db_float_on_the_surface(db):
    from app.modules.subscriptions.schemas import SubscriptionOut

    sub = _add(db, name="Netflix", amount=12.99)
    assert isinstance(sub.amount, Decimal)
    out = SubscriptionOut.model_validate(sub)
    assert isinstance(out.amount, float)
    assert out.amount == 12.99


def test_update_and_delete(db):
    sub = _add(db, name="Spotify", amount=9.99)
    service.update_subscription(db, 1, sub.id, amount=12.99)
    assert service.get_subscription(db, 1, sub.id).amount == Decimal("12.99")
    assert service.delete_subscription(db, 1, sub.id) is True
    assert service.get_subscription(db, 1, sub.id) is None


def test_upcoming_includes_overdue_and_orders_by_date(db):
    today = date.today()
    _add(db, name="Scaduta", amount=5, next_renewal=today - timedelta(days=2))
    _add(db, name="Domani", amount=5, next_renewal=today + timedelta(days=1))
    _add(db, name="Lontana", amount=5, next_renewal=today + timedelta(days=400))
    soon = service.upcoming(db, 1, days=30)
    assert [s.name for s in soon] == ["Scaduta", "Domani"]


def test_severity_buckets(db):
    today = date.today()
    assert service._severity_for(today - timedelta(days=1)) == "danger"
    assert service._severity_for(today + timedelta(days=3)) == "warning"
    assert service._severity_for(today + timedelta(days=20)) == "info"


def test_summary_headline_and_stats(db):
    _add(db, name="Netflix", amount=12.0, cycle="monthly", next_renewal=date.today() + timedelta(days=5))
    summary = service.summary(db, 1)
    assert "/mese" in summary.headline
    labels = {s.label for s in summary.stats}
    assert {"Attive", "€/mese", "€/anno"} <= labels


def test_summary_lists_every_active_sub_not_just_upcoming(db):
    """Far-future and undated subs must still appear in the card preview."""
    today = date.today()
    _add(db, name="Presto", amount=5, next_renewal=today + timedelta(days=3))
    _add(db, name="Lontana", amount=5, next_renewal=today + timedelta(days=300))  # yearly Amazon-like
    _add(db, name="Senza data", amount=5, next_renewal=None)
    summary = service.summary(db, 1)
    titles = [i.title for i in summary.items]
    assert any("Presto" in t for t in titles)
    assert any("Lontana" in t for t in titles)   # the bug: this was hidden before
    assert any("Senza data" in t for t in titles)
    # soonest first, undated last
    assert titles[0].startswith("Presto")
    assert titles[-1].startswith("Senza data")


# --- MCP agent surface --------------------------------------------------- #
def test_mcp_update_edits_in_place_no_duplicate(db):
    """Hermes editing a sub must change the row, not create a second one."""
    from app.modules.subscriptions import mcp

    sub = _add(db, name="Amazon Prime", amount=49.9, cycle="yearly")
    db.commit()

    res = mcp.subscriptions_update(sub.id, amount=59.9, next_renewal="2026-12-15")
    assert res["id"] == sub.id
    assert res["amount"] == 59.9
    assert res["next_renewal"] == "2026-12-15"
    # still exactly one row
    assert len(service.list_subscriptions(db, 1)) == 1


def test_mcp_update_unknown_id_returns_error(db):
    from app.modules.subscriptions import mcp

    assert "error" in mcp.subscriptions_update(999, amount=1.0)


def test_mcp_delete_removes_duplicate(db):
    from app.modules.subscriptions import mcp

    sub = _add(db, name="Doppione", amount=5)
    db.commit()
    assert mcp.subscriptions_delete(sub.id) == {"deleted": True, "id": sub.id}
    db.expunge_all()  # tool deleted in its own session; drop our identity-map cache
    assert service.get_subscription(db, 1, sub.id) is None
    assert "error" in mcp.subscriptions_delete(sub.id)  # already gone


# --- REST ---------------------------------------------------------------- #
def test_rest_add_and_cost(client):
    client.post("/api/modules/subscriptions/subscriptions",
                json={"name": "Netflix", "amount": 12.0, "cycle": "monthly"})
    r = client.get("/api/modules/subscriptions/subscriptions/cost")
    assert r.status_code == 200
    # cost endpoint returns the monthly figure as a number
    body = r.json()
    assert float(body["monthly"]) == 12.0
