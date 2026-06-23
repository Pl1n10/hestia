"""Identity resolution + token handling."""

from __future__ import annotations

import pytest

from app.auth.providers import hash_token, resolve_principal, verify_token
from app.core_models import ApiToken
from app.settings import settings


def test_hash_is_deterministic_and_hex():
    h = hash_token("secret")
    assert h == hash_token("secret")
    assert len(h) == 64
    assert h != "secret"


def test_verify_token_constant_time_compare():
    assert verify_token("secret", hash_token("secret"))
    assert not verify_token("wrong", hash_token("secret"))


def test_env_master_token_resolves_to_agent(db):
    p = resolve_principal({"Authorization": f"Bearer {settings.agent_token}"}, db)
    assert p is not None and p.is_agent
    assert p.household_id == settings.default_household_id


def test_db_token_resolves_and_updates_last_used(db, household):
    plain = "hestia_db_token_xyz"
    db.add(
        ApiToken(
            household_id=1, name="hermes", token_hash=hash_token(plain), principal_name="hermes"
        )
    )
    db.commit()

    p = resolve_principal({"Authorization": f"Bearer {plain}"}, db)
    assert p is not None and p.is_agent and p.display_name == "hermes"

    row = db.query(ApiToken).filter_by(token_hash=hash_token(plain)).one()
    assert row.last_used_at is not None


def test_invalid_bearer_does_not_fall_through_to_dev(db, monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "dev")
    p = resolve_principal({"Authorization": "Bearer nope"}, db)
    assert p is None


def test_dev_mode_provisions_dev_user(db, monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "dev")
    p = resolve_principal({}, db)
    assert p is not None and p.is_human
    assert p.display_name == settings.dev_user_name


def test_proxy_mode_trusts_identity_header(db, monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "proxy")
    headers = {settings.proxy_user_header: "compagna", settings.proxy_email_header: "c@casa.local"}
    p = resolve_principal(headers, db)
    assert p is not None and p.is_human and p.display_name == "compagna"


def test_proxy_mode_without_header_is_unauthenticated(db, monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "proxy")
    assert resolve_principal({}, db) is None


def test_strict_mode_requires_token(db, monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "strict")
    assert resolve_principal({}, db) is None
    p = resolve_principal({"Authorization": f"Bearer {settings.agent_token}"}, db)
    assert p is not None and p.is_agent
