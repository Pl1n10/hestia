"""Dogs module — the append-mostly activity-log shape."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.dogs import service


def test_create_and_list_dog(db):
    service.create_dog(db, 1, name="Milka", breed="Berger Picard")
    dogs = service.list_dogs(db, 1)
    assert len(dogs) == 1 and dogs[0].name == "Milka"


def test_household_scoping(db):
    service.create_dog(db, 1, name="Milka")
    service.create_dog(db, 2, name="Altrui")
    assert [d.name for d in service.list_dogs(db, 1)] == ["Milka"]


def test_find_dog_by_name_is_case_insensitive(db):
    service.create_dog(db, 1, name="Milka")
    assert service.find_dog_by_name(db, 1, "milka") is not None
    assert service.find_dog_by_name(db, 1, "MILKA") is not None
    assert service.find_dog_by_name(db, 1, "rex") is None


def test_log_activity_and_recent_order(db):
    dog = service.create_dog(db, 1, name="Milka")
    now = datetime.now(timezone.utc)
    service.log_activity(db, 1, dog.id, type="pappa", occurred_at=now - timedelta(hours=2))
    service.log_activity(db, 1, dog.id, type="sgambamento", occurred_at=now)
    recent = service.recent_activities(db, 1)
    assert [a.type for a in recent] == ["sgambamento", "pappa"]


def test_summary_headline_reflects_last_activity(db):
    dog = service.create_dog(db, 1, name="Milka")
    service.log_activity(db, 1, dog.id, type="sgambamento")
    summary = service.summary(db, 1)
    assert "Milka" in summary.headline
    assert "sgambamento" in summary.headline
    assert summary.stats[0].value == "1"  # one dog


def test_summary_empty_state(db):
    summary = service.summary(db, 1)
    assert "Nessun cane" in summary.headline


# --- REST ---------------------------------------------------------------- #
def test_rest_create_dog_and_log(client):
    r = client.post("/api/modules/dogs/dogs", json={"name": "Milka", "breed": "Berger Picard"})
    assert r.status_code == 201
    dog_id = r.json()["id"]

    r = client.post(
        f"/api/modules/dogs/dogs/{dog_id}/activities",
        json={"type": "sgambamento", "duration_min": 30},
    )
    assert r.status_code == 201
    assert r.json()["logged_by"] == "Roberto"  # dev user attribution


def test_rest_attribution_for_agent(client, agent_headers):
    r = client.post("/api/modules/dogs/dogs", json={"name": "Milka"}, headers=agent_headers)
    dog_id = r.json()["id"]
    r = client.post(
        f"/api/modules/dogs/dogs/{dog_id}/activities",
        json={"type": "pappa"},
        headers=agent_headers,
    )
    assert r.status_code == 201
    assert r.json()["logged_by"] == "hermes"
