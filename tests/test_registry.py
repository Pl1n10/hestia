"""Module registry + discovery."""

from __future__ import annotations

import pytest

from app.modules import AVAILABLE, enabled_keys, load_enabled
from app.modules.base import get_module, get_registry


def test_enabled_modules_are_loaded():
    reg = load_enabled()
    assert "dogs" in reg
    assert "subscriptions" in reg


def test_each_module_exposes_the_contract():
    for module in load_enabled().values():
        assert module.manifest.key
        assert module.router is not None
        assert callable(module.summary_fn)
        # tools are optional but, if present, must be McpTool-shaped
        for tool in module.mcp_tools:
            assert tool.name and callable(tool.handler)


def test_get_module_by_key():
    load_enabled()
    assert get_module("dogs") is not None
    assert get_module("does-not-exist") is None


def test_template_is_not_discovered():
    assert "_template" not in AVAILABLE
    assert "example" not in load_enabled()


def test_enabled_keys_falls_back_to_available(monkeypatch):
    from app.settings import settings

    monkeypatch.setattr(settings, "enabled_modules", [])
    assert enabled_keys() == list(AVAILABLE)


def test_registry_snapshot_is_a_copy():
    reg = get_registry()
    reg.clear()  # mutating the copy must not affect the live registry
    assert "dogs" in get_registry()
