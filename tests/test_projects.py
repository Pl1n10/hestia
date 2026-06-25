"""Projects module — cross-project development overview.

Covers the CRUD lifecycle, household scoping, summary card, REST surface,
and MCP tools.
"""

from __future__ import annotations

from app.modules.projects import service


# --- service ------------------------------------------------------------- #
def test_create_defaults_to_active(db):
    proj = service.create_project(db, 1, name="hestia")
    assert proj.status == "active"
    assert proj.repo_url is None
    assert proj.last_activity is None


def test_unknown_status_falls_back_to_active(db):
    proj = service.create_project(db, 1, name="X", status="flying")
    assert proj.status == "active"


def test_household_scoping(db):
    service.create_project(db, 1, name="mine")
    service.create_project(db, 2, name="theirs")
    assert [p.name for p in service.list_projects(db, 1)] == ["mine"]


def test_list_alphabetical(db):
    service.create_project(db, 1, name="zebra")
    service.create_project(db, 1, name="alpha")
    assert [p.name for p in service.list_projects(db, 1)] == ["alpha", "zebra"]


def test_list_status_filter(db):
    service.create_project(db, 1, name="active-one", status="active")
    service.create_project(db, 1, name="paused-one", status="paused")
    service.create_project(db, 1, name="done-one", status="completed")

    active = service.list_projects(db, 1, status="active")
    assert [p.name for p in active] == ["active-one"]


def test_list_active_only_excludes_completed(db):
    service.create_project(db, 1, name="a", status="active")
    service.create_project(db, 1, name="p", status="paused")
    service.create_project(db, 1, name="c", status="completed")
    names = {p.name for p in service.list_projects(db, 1, active_only=True)}
    assert names == {"a", "p"}
    assert "c" not in names


def test_get_project(db):
    proj = service.create_project(db, 1, name="argus")
    fetched = service.get_project(db, 1, proj.id)
    assert fetched is not None
    assert fetched.name == "argus"


def test_get_wrong_household_returns_none(db):
    proj = service.create_project(db, 1, name="argus")
    assert service.get_project(db, 2, proj.id) is None


def test_update_status(db):
    proj = service.create_project(db, 1, name="sidebiz")
    updated = service.update_project(db, 1, proj.id, status="paused")
    assert updated.status == "paused"


def test_update_ignores_unknown_status(db):
    proj = service.create_project(db, 1, name="X")
    service.update_project(db, 1, proj.id, status="bogus", repo_url="https://example.com")
    fresh = service.get_project(db, 1, proj.id)
    assert fresh.status == "active"          # bogus ignored
    assert fresh.repo_url == "https://example.com"  # valid change applied


def test_update_last_activity(db):
    proj = service.create_project(db, 1, name="nekontrol")
    updated = service.update_project(
        db, 1, proj.id, last_activity="merged PR #42: add winget support"
    )
    assert updated.last_activity == "merged PR #42: add winget support"


def test_delete(db):
    proj = service.create_project(db, 1, name="temp")
    assert service.delete_project(db, 1, proj.id) is True
    assert service.get_project(db, 1, proj.id) is None


def test_delete_returns_false_on_missing(db):
    assert service.delete_project(db, 1, 99999) is False


# --- summary ------------------------------------------------------------- #
def test_summary_empty(db):
    s = service.summary(db, 1)
    assert "Nessun progetto" in s.headline
    assert s.items == []


def test_summary_headline_with_active_and_paused(db):
    service.create_project(db, 1, name="a", status="active")
    service.create_project(db, 1, name="b", status="active")
    service.create_project(db, 1, name="c", status="paused")
    s = service.summary(db, 1)
    assert "2 attivi" in s.headline
    assert "1 in pausa" in s.headline


def test_summary_all_completed(db):
    service.create_project(db, 1, name="done", status="completed")
    s = service.summary(db, 1)
    assert "Tutti completati" in s.headline


def test_summary_stats_labels(db):
    service.create_project(db, 1, name="x")
    s = service.summary(db, 1)
    labels = {st.label for st in s.stats}
    assert {"Attivi", "In pausa", "Completati"} <= labels


def test_summary_items_show_active_and_paused_not_completed(db):
    service.create_project(db, 1, name="live", status="active")
    service.create_project(db, 1, name="rest", status="paused")
    service.create_project(db, 1, name="done", status="completed")
    s = service.summary(db, 1)
    item_titles = {i.title for i in s.items}
    assert "live" in item_titles
    assert "rest" in item_titles
    assert "done" not in item_titles


def test_summary_item_count_equals_active_plus_paused(db):
    service.create_project(db, 1, name="a1", status="active")
    service.create_project(db, 1, name="a2", status="active")
    service.create_project(db, 1, name="p1", status="paused")
    service.create_project(db, 1, name="c1", status="completed")
    s = service.summary(db, 1)
    assert len(s.items) == 3  # 2 active + 1 paused


# --- REST ---------------------------------------------------------------- #
def test_rest_create_and_list(client):
    r = client.post(
        "/api/modules/projects/projects",
        json={
            "name": "hestia",
            "description": "Household dashboard",
            "status": "active",
            "repo_url": "https://github.com/Pl1n10/hestia",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "active"
    assert body["repo_url"] == "https://github.com/Pl1n10/hestia"

    r2 = client.get("/api/modules/projects/projects")
    assert r2.status_code == 200
    assert any(p["name"] == "hestia" for p in r2.json())


def test_rest_update(client):
    r = client.post("/api/modules/projects/projects", json={"name": "argus"})
    proj_id = r.json()["id"]

    r2 = client.patch(
        f"/api/modules/projects/projects/{proj_id}",
        json={"status": "paused", "last_activity": "refactor: extract poller"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "paused"
    assert body["last_activity"] == "refactor: extract poller"


def test_rest_delete(client):
    r = client.post("/api/modules/projects/projects", json={"name": "temp"})
    proj_id = r.json()["id"]

    r2 = client.delete(f"/api/modules/projects/projects/{proj_id}")
    assert r2.status_code == 204

    r3 = client.get(f"/api/modules/projects/projects/{proj_id}")
    assert r3.status_code == 404


def test_rest_404_on_missing(client):
    assert client.get("/api/modules/projects/projects/99999").status_code == 404


def test_rest_status_filter(client):
    client.post("/api/modules/projects/projects", json={"name": "active-proj", "status": "active"})
    client.post("/api/modules/projects/projects", json={"name": "done-proj", "status": "completed"})

    r = client.get("/api/modules/projects/projects?status=completed")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert names == ["done-proj"]


# --- MCP ----------------------------------------------------------------- #
def test_mcp_add_writes_through_service(db):
    from app.modules.projects import mcp

    result = mcp.projects_add(
        name="sidebiz",
        description="Side-business scouting agent",
        status="active",
        repo_url="https://github.com/Pl1n10/sidebiz",
        last_activity="shipped gig mode",
    )
    assert result["status"] == "active"
    assert result["last_activity"] == "shipped gig mode"

    rows = service.list_projects(db, 1)
    assert any(p.name == "sidebiz" for p in rows)


def test_mcp_list(db):
    from app.modules.projects import mcp

    mcp.projects_add(name="a")
    mcp.projects_add(name="b", status="completed")

    all_proj = mcp.projects_list()
    assert len(all_proj) == 2

    active_only = mcp.projects_list(active_only=True)
    assert len(active_only) == 1
    assert active_only[0]["name"] == "a"


def test_mcp_update_records_activity(db):
    from app.modules.projects import mcp

    created = mcp.projects_add(name="nekontrol")
    result = mcp.projects_update(
        project_id=created["id"],
        last_activity="fix: agent reconnect on timeout",
    )
    assert result["last_activity"] == "fix: agent reconnect on timeout"
    assert result["last_activity_at"] is not None


def test_mcp_update_invalid_status(db):
    from app.modules.projects import mcp

    created = mcp.projects_add(name="X")
    result = mcp.projects_update(project_id=created["id"], status="flying")
    assert "error" in result
    assert "valid" in result


def test_mcp_update_unknown_id(db):
    from app.modules.projects import mcp

    result = mcp.projects_update(project_id=999999, name="ghost")
    assert "error" in result


def test_mcp_delete(db):
    from app.modules.projects import mcp

    created = mcp.projects_add(name="temp")
    result = mcp.projects_delete(created["id"])
    assert result == {"deleted": created["id"]}

    rows = service.list_projects(db, 1)
    assert not any(p.id == created["id"] for p in rows)


def test_mcp_delete_unknown_id(db):
    from app.modules.projects import mcp

    result = mcp.projects_delete(999999)
    assert "error" in result
