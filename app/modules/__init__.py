"""Module discovery + loading.

Importing a module package (``app.modules.<key>``) is what (a) registers its
ORM models on ``Base.metadata`` and (b) registers its ``DashboardModule`` in
the registry. We only import the *enabled* set, so disabled modules cost
nothing and create no tables.

``_template`` is intentionally excluded from discovery: it is the copy-me
blueprint used by ``scripts/new_module.py``, not a live module.
"""

from __future__ import annotations

import importlib

from app.modules.base import DashboardModule, get_registry
from app.settings import settings

# Modules shipped in-tree and available to enable.
AVAILABLE: tuple[str, ...] = ("dogs", "subscriptions")


def enabled_keys() -> list[str]:
    return list(settings.enabled_modules) if settings.enabled_modules else list(AVAILABLE)


def load_enabled() -> dict[str, DashboardModule]:
    """Import every enabled module package, then return the registry."""
    for key in enabled_keys():
        importlib.import_module(f"app.modules.{key}")
    return get_registry()
