"""Tiles module — custom personalizable dashboard tiles."""

from __future__ import annotations

from datetime import date, timedelta

from app.modules.tiles import service


def _add(db, **kw) -> object:
    kw.setdefault("title", "Test Tile")
    return service.create_tile(db, 1, **kw)


# --- service layer ------------------------------------------------------- #

def test_create_and_list_tile(db):
    _add(db, title="Manutenzione Cucina")
    tiles = service.list_tiles(db, 1)
    assert len(tiles) == 1
    assert tiles[0].title == "Manutenzione Cucina"


def test_household_scoping(db):
    _add(db, title="Casa mia")
    service.create_tile(db, 2, title="Casa altrui")
    assert [t.title for t in service.list_tiles(db, 1)] == ["Casa mia"]
    assert [t.title for t in service.list_tiles(db, 2)] == ["Casa altrui"]


def test_inactive_tile_hidden_by_default(db):
    _add(db, title="Attivo")
    _add(db, title="Nascosto", active=False)
    active = service.list_tiles(db, 1, active_only=True)
    assert len(active) == 1
    assert active[0].title == "Attivo"


def test_list_all_includes_inactive(db):
    _add(db, title="Attivo")
    _add(db, title="Nascosto", active=False)
    all_tiles = service.list_tiles(db, 1, active_only=False)
    assert len(all_tiles) == 2


def test_get_tile(db):
    t = _add(db, title="Specifica")
    found = service.get_tile(db, 1, t.id)
    assert found is not None and found.title == "Specifica"


def test_get_tile_wrong_household_returns_none(db):
    t = _add(db, title="Mia")
    assert service.get_tile(db, 2, t.id) is None


def test_update_tile(db):
    t = _add(db, title="Vecchio", color="default")
    updated = service.update_tile(db, 1, t.id, title="Nuovo", color="blue")
    assert updated.title == "Nuovo"
    assert updated.color == "blue"


def test_update_unknown_tile_returns_none(db):
    assert service.update_tile(db, 1, 999, title="X") is None


def test_delete_tile(db):
    t = _add(db, title="Da eliminare")
    assert service.delete_tile(db, 1, t.id) is True
    assert service.get_tile(db, 1, t.id) is None


def test_delete_unknown_tile_returns_false(db):
    assert service.delete_tile(db, 1, 999) is False


# --- severity ------------------------------------------------------------ #

def test_severity_overdue(db):
    assert service._severity_for(date.today() - timedelta(days=1)) == "danger"


def test_severity_today_and_tomorrow(db):
    assert service._severity_for(date.today()) == "warning"
    assert service._severity_for(date.today() + timedelta(days=1)) == "warning"


def test_severity_within_week(db):
    assert service._severity_for(date.today() + timedelta(days=5)) == "info"


def test_severity_far_future_and_none(db):
    assert service._severity_for(date.today() + timedelta(days=30)) == "normal"
    assert service._severity_for(None) == "normal"


# --- overdue count ------------------------------------------------------- #

def test_overdue_count(db):
    today = date.today()
    _add(db, title="Scaduto", next_check_at=today - timedelta(days=3))
    _add(db, title="Futuro", next_check_at=today + timedelta(days=5))
    _add(db, title="Senza data")
    assert service.overdue_count(db, 1) == 1


# --- summary ------------------------------------------------------------- #

def test_summary_empty_state(db):
    s = service.summary(db, 1)
    assert "Nessun riquadro" in s.headline
    assert s.stats[0].value == "0"


def test_summary_headline_overdue(db):
    _add(db, title="Caldaia", next_check_at=date.today() - timedelta(days=2))
    s = service.summary(db, 1)
    assert "Caldaia" in s.headline
    assert "scadenza" in s.headline


def test_summary_headline_upcoming(db):
    _add(db, title="Filtro", next_check_at=date.today() + timedelta(days=10))
    s = service.summary(db, 1)
    assert "Filtro" in s.headline


def test_summary_headline_no_dates(db):
    _add(db, title="Nota A")
    _add(db, title="Nota B")
    s = service.summary(db, 1)
    assert "attiv" in s.headline


def test_summary_lists_all_active_tiles(db):
    """All active tiles must appear in items, not just urgent ones (anti-pattern guard)."""
    today = date.today()
    _add(db, title="Overdue", next_check_at=today - timedelta(days=1))
    _add(db, title="Futuro", next_check_at=today + timedelta(days=60))
    _add(db, title="SenzaData")
    s = service.summary(db, 1)
    titles = [i.title for i in s.items]
    assert "Overdue" in titles
    assert "Futuro" in titles
    assert "SenzaData" in titles


def test_summary_items_sorted_overdue_first(db):
    today = date.today()
    _add(db, title="Futuro", next_check_at=today + timedelta(days=5))
    _add(db, title="Overdue", next_check_at=today - timedelta(days=1))
    _add(db, title="SenzaData")
    s = service.summary(db, 1)
    titles = [i.title for i in s.items]
    assert titles[0] == "Overdue"
    assert titles[-1] == "SenzaData"


def test_summary_stats(db):
    today = date.today()
    _add(db, title="Ok", next_check_at=today + timedelta(days=5))
    _add(db, title="Scaduto", next_check_at=today - timedelta(days=2))
    s = service.summary(db, 1)
    labels = {st.label: st.value for st in s.stats}
    assert labels["Attivi"] == "2"
    assert labels["In scadenza"] == "1"


# --- REST ---------------------------------------------------------------- #

def test_rest_create_and_list(client):
    r = client.post(
        "/api/modules/tiles/tiles",
        json={
            "title": "Manutenzione Cucina",
            "body": "Ultima manutenzione: 22 giugno 2026",
            "color": "green",
            "next_check_at": "2026-09-22",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Manutenzione Cucina"
    assert data["next_check_at"] == "2026-09-22"

    r = client.get("/api/modules/tiles/tiles")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_rest_get_tile(client):
    r = client.post("/api/modules/tiles/tiles", json={"title": "Promemoria"})
    tile_id = r.json()["id"]
    r = client.get(f"/api/modules/tiles/tiles/{tile_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Promemoria"


def test_rest_get_tile_not_found(client):
    r = client.get("/api/modules/tiles/tiles/999")
    assert r.status_code == 404


def test_rest_update_tile(client):
    r = client.post("/api/modules/tiles/tiles", json={"title": "Vecchio"})
    tile_id = r.json()["id"]
    r = client.patch(f"/api/modules/tiles/tiles/{tile_id}", json={"title": "Aggiornato", "color": "blue"})
    assert r.status_code == 200
    assert r.json()["title"] == "Aggiornato"
    assert r.json()["color"] == "blue"


def test_rest_update_tile_not_found(client):
    r = client.patch("/api/modules/tiles/tiles/999", json={"title": "X"})
    assert r.status_code == 404


def test_rest_delete_tile(client):
    r = client.post("/api/modules/tiles/tiles", json={"title": "Elimina"})
    tile_id = r.json()["id"]
    r = client.delete(f"/api/modules/tiles/tiles/{tile_id}")
    assert r.status_code == 204
    r = client.get(f"/api/modules/tiles/tiles/{tile_id}")
    assert r.status_code == 404


def test_rest_delete_tile_not_found(client):
    r = client.delete("/api/modules/tiles/tiles/999")
    assert r.status_code == 404


def test_rest_list_includes_inactive_when_asked(client):
    r = client.post("/api/modules/tiles/tiles", json={"title": "Attivo"})
    tile_id = r.json()["id"]
    client.patch(f"/api/modules/tiles/tiles/{tile_id}", json={"active": False})
    r = client.get("/api/modules/tiles/tiles?active_only=false")
    assert r.status_code == 200
    assert any(t["title"] == "Attivo" for t in r.json())


# --- MCP agent surface --------------------------------------------------- #

def test_mcp_add_and_list(db):
    from app.modules.tiles import mcp

    result = mcp.tiles_add(
        title="Manutenzione Cucina",
        body="Ultima manutenzione: 22 giugno 2026",
        color="green",
        next_check_at="2026-09-22",
    )
    assert result["title"] == "Manutenzione Cucina"
    assert result["next_check_at"] == "2026-09-22"

    rows = mcp.tiles_list()
    assert len(rows) == 1
    assert rows[0]["title"] == "Manutenzione Cucina"


def test_mcp_update_edits_in_place(db):
    from app.modules.tiles import mcp

    t = mcp.tiles_add(title="Impianto Idraulico", color="default")
    result = mcp.tiles_update(t["id"], color="blue", next_check_at="2027-01-01")
    assert result["id"] == t["id"]
    assert result["color"] == "blue"
    assert result["next_check_at"] == "2027-01-01"
    assert len(mcp.tiles_list()) == 1


def test_mcp_update_unknown_id_returns_error(db):
    from app.modules.tiles import mcp

    assert "error" in mcp.tiles_update(999, title="X")


def test_mcp_delete(db):
    from app.modules.tiles import mcp

    t = mcp.tiles_add(title="Temporaneo")
    result = mcp.tiles_delete(t["id"])
    assert result == {"deleted": True, "id": t["id"]}
    assert mcp.tiles_list() == []
    assert "error" in mcp.tiles_delete(t["id"])


def test_mcp_deactivate_hides_from_default_list(db):
    from app.modules.tiles import mcp

    t = mcp.tiles_add(title="Sospeso")
    mcp.tiles_update(t["id"], active=False)
    assert mcp.tiles_list(active_only=True) == []
    assert len(mcp.tiles_list(active_only=False)) == 1
