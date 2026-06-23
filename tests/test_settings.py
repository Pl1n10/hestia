"""Settings: the CSV-from-env fix is a regression guard (docs/FAILURES.md F-003)."""

from __future__ import annotations

from app.settings import Settings


def test_enabled_modules_parses_csv_from_env(monkeypatch):
    monkeypatch.setenv("HESTIA_ENABLED_MODULES", "dogs, subscriptions ,vehicles")
    s = Settings()
    assert s.enabled_modules == ["dogs", "subscriptions", "vehicles"]


def test_enabled_modules_empty_when_unset(monkeypatch):
    monkeypatch.delenv("HESTIA_ENABLED_MODULES", raising=False)
    s = Settings()
    assert s.enabled_modules == []


def test_enabled_modules_accepts_list_in_code():
    s = Settings(enabled_modules=["dogs"])
    assert s.enabled_modules == ["dogs"]


def test_env_prefix_applies(monkeypatch):
    monkeypatch.setenv("HESTIA_APP_NAME", "Focolare")
    assert Settings().app_name == "Focolare"
