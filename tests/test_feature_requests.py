"""Feature-requests module — the agent's channel for asking the dashboard to grow.

Covers the lifecycle (new -> in_progress -> done/rejected), household scoping,
the REST surface, and the MCP tools Hermes calls.
"""

from __future__ import annotations

from app.modules.feature_requests import service


# --- service ------------------------------------------------------------- #
def test_create_defaults_to_new_and_normal(db):
    req = service.create_request(db, 1, title="Track car insurance")
    assert req.status == "new"
    assert req.priority == "normal"


def test_unknown_priority_falls_back_to_normal(db):
    req = service.create_request(db, 1, title="X", priority="urgent")
    assert req.priority == "normal"


def test_household_scoping(db):
    service.create_request(db, 1, title="Mine")
    service.create_request(db, 2, title="Theirs")
    assert [r.title for r in service.list_requests(db, 1)] == ["Mine"]


def test_list_open_only_excludes_done_and_rejected(db):
    a = service.create_request(db, 1, title="A")
    b = service.create_request(db, 1, title="B")
    service.set_status(db, 1, a.id, "done")
    service.set_status(db, 1, b.id, "in_progress")
    open_titles = {r.title for r in service.list_requests(db, 1, open_only=True)}
    assert open_titles == {"B"}


def test_list_newest_first(db):
    service.create_request(db, 1, title="First")
    service.create_request(db, 1, title="Second")
    assert [r.title for r in service.list_requests(db, 1)] == ["Second", "First"]


def test_set_status_with_resolution(db):
    req = service.create_request(db, 1, title="Add dark mode")
    updated = service.set_status(db, 1, req.id, "done", resolution="shipped in PR #12")
    assert updated.status == "done"
    assert updated.resolution == "shipped in PR #12"


def test_set_unknown_status_is_rejected(db):
    req = service.create_request(db, 1, title="X")
    assert service.set_status(db, 1, req.id, "wat") is None
    # the row keeps its original status
    assert service.get_request(db, 1, req.id).status == "new"


def test_update_ignores_unknown_status(db):
    req = service.create_request(db, 1, title="X")
    service.update_request(db, 1, req.id, status="bogus", priority="high")
    fresh = service.get_request(db, 1, req.id)
    assert fresh.status == "new"      # bogus ignored
    assert fresh.priority == "high"   # valid change applied


def test_delete(db):
    req = service.create_request(db, 1, title="Temp")
    assert service.delete_request(db, 1, req.id) is True
    assert service.get_request(db, 1, req.id) is None


def test_summary_empty_and_populated(db):
    assert "Nessuna richiesta" in service.summary(db, 1).headline

    a = service.create_request(db, 1, title="A", priority="high")
    service.create_request(db, 1, title="B")
    service.set_status(db, 1, a.id, "in_progress")
    summary = service.summary(db, 1)
    assert "in corso" in summary.headline
    labels = {s.label for s in summary.stats}
    assert {"Aperte", "In corso", "Fatte"} <= labels


# --- REST ---------------------------------------------------------------- #
def test_rest_create_lists_and_updates(client):
    r = client.post(
        "/api/modules/feature_requests/requests",
        json={"title": "Add vehicles module", "detail": "bollo + assicurazione", "priority": "high"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "new"
    assert body["requested_by"] == "Roberto"  # dev user attribution
    req_id = body["id"]

    r = client.patch(
        f"/api/modules/feature_requests/requests/{req_id}",
        json={"status": "in_progress"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


def test_rest_explicit_requested_by_wins(client):
    r = client.post(
        "/api/modules/feature_requests/requests",
        json={"title": "From partner", "requested_by": "Giulia"},
    )
    assert r.json()["requested_by"] == "Giulia"


def test_rest_404_on_missing(client):
    assert client.get("/api/modules/feature_requests/requests/999").status_code == 404


# --- MCP (the Hermes surface) ------------------------------------------- #
def test_mcp_add_writes_through_service(db):
    from app.modules.feature_requests import mcp

    result = mcp.feature_requests_add(
        title="Track utility bills", detail="from Gmail", priority="high", requested_by="Roberto"
    )
    assert result["status"] == "new"
    assert result["requested_by"] == "Roberto"

    # visible to the service / REST the same instant (default household is 1)
    rows = service.list_requests(db, 1)
    assert [r.title for r in rows] == ["Track utility bills"]


def test_mcp_add_defaults_requester_to_hermes(db):
    from app.modules.feature_requests import mcp

    result = mcp.feature_requests_add(title="Something")
    assert result["requested_by"] == "hermes"


def test_mcp_set_status_validates(db):
    from app.modules.feature_requests import mcp

    created = mcp.feature_requests_add(title="X")
    bad = mcp.feature_requests_set_status(created["id"], "nope")
    assert "error" in bad and "valid" in bad

    ok = mcp.feature_requests_set_status(created["id"], "done", resolution="done")
    assert ok["status"] == "done"


def test_mcp_set_status_unknown_id(db):
    from app.modules.feature_requests import mcp

    assert "error" in mcp.feature_requests_set_status(123456, "done")


def test_mcp_list_open_only_by_default(db):
    from app.modules.feature_requests import mcp

    mcp.feature_requests_add(title="open one")
    b = mcp.feature_requests_add(title="closed one")
    mcp.feature_requests_set_status(b["id"], "done")
    titles = {r["title"] for r in mcp.feature_requests_list()}
    assert titles == {"open one"}
