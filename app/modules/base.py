"""The module contract and the in-process registry.

A *module* is a self-contained vertical (dogs, subscriptions, vehicles, ...).
It plugs three things into the dashboard:

* a REST ``router`` (mounted under ``/api/modules/<key>``)
* a ``summary_fn`` that feeds the home view's card for that module
* zero or more ``mcp_tools`` so agents (Hermes, a future Alexa skill) can
  read/write the same data the humans see in the app

The golden rule (see DECISIONS.md D-002): **all surfaces are thin adapters
over a module's ``service.py``**. The REST router and the MCP tools both call
the same service functions, so the API and the agent can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session


# --------------------------------------------------------------------------- #
# Manifest + summary shapes
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ModuleManifest:
    key: str  # url-safe, unique, e.g. "dogs"
    name: str  # human label, e.g. "Cani"
    icon: str  # emoji or icon id for the card
    version: str
    description: str


class StatItem(BaseModel):
    label: str
    value: str


class SummaryItem(BaseModel):
    title: str
    subtitle: str | None = None
    when: str | None = None
    severity: str = "normal"  # normal | info | warning | danger


class ModuleSummary(BaseModel):
    """What a module contributes to the home dashboard."""

    key: str
    name: str
    icon: str
    headline: str
    stats: list[StatItem] = []
    items: list[SummaryItem] = []


# --------------------------------------------------------------------------- #
# Agent surface
# --------------------------------------------------------------------------- #
@dataclass
class McpTool:
    """A capability exposed to agents.

    ``handler`` is a plain function with type-annotated args (FastMCP derives
    the JSON schema from them). It opens its own DB session and resolves the
    household itself, because the MCP server runs as its own process.
    """

    name: str
    description: str
    handler: Callable[..., object]


# --------------------------------------------------------------------------- #
# The module itself
# --------------------------------------------------------------------------- #
@dataclass
class DashboardModule:
    manifest: ModuleManifest
    router: APIRouter
    summary_fn: Callable[[Session, int], ModuleSummary]
    mcp_tools: list[McpTool] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.manifest.key


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
_REGISTRY: dict[str, DashboardModule] = {}


def register(module: DashboardModule) -> DashboardModule:
    """Register (or replace) a module by key. Called at import time."""
    _REGISTRY[module.key] = module
    return module


def get_registry() -> dict[str, DashboardModule]:
    return dict(_REGISTRY)


def get_module(key: str) -> DashboardModule | None:
    return _REGISTRY.get(key)


def clear_registry() -> None:
    """Test helper."""
    _REGISTRY.clear()
