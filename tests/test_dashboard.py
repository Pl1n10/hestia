"""System API surface + dashboard aggregation."""

from __future__ import annotations

import pytest


def test_health_is_open(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_me_in_dev_mode_is_the_dev_user(client):
    r = client.get("/api/me")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "human"
    assert body["household_id"] == 1


def test_me_as_agent(client, agent_headers):
    r = client.get("/api/me", headers=agent_headers)
    assert r.status_code == 200
    assert r.json()["kind"] == "agent"


def test_modules_lists_manifests_and_tools(client):
    r = client.get("/api/modules")
    assert r.status_code == 200
    keys = {m["key"] for m in r.json()}
    assert {"dogs", "subscriptions"} <= keys
    dogs = next(m for m in r.json() if m["key"] == "dogs")
    assert "dogs_log_activity" in dogs["tools"]


def test_dashboard_returns_one_card_per_module(client):
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    cards = r.json()
    assert {c["key"] for c in cards} == {"dogs", "subscriptions", "feature_requests"}
    for c in cards:
        assert "headline" in c and "icon" in c


def test_integrations_report_configuration_state(client):
    r = client.get("/api/integrations")
    assert r.status_code == 200
    names = {i["name"] for i in r.json()}
    assert "Gmail" in names
    # stubs ship unconfigured
    assert all(i["configured"] is False for i in r.json())


def test_one_broken_module_does_not_break_the_home(client, monkeypatch):
    """A module whose summary raises must yield an error card, not a 500."""
    from app.modules.base import get_module

    def boom(_db, _hh):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(get_module("dogs"), "summary_fn", boom)

    r = client.get("/api/dashboard")
    assert r.status_code == 200
    dogs_card = next(c for c in r.json() if c["key"] == "dogs")
    assert dogs_card["icon"] == "⚠️"
    assert "kaboom" in dogs_card["headline"]
    # the healthy module is still present
    assert any(c["key"] == "subscriptions" for c in r.json())
