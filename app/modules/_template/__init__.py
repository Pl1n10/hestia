"""TEMPLATE module package. Copy, then register in app/modules/__init__.py
(AVAILABLE) or enable via HESTIA_ENABLED_MODULES."""

from app.modules.base import DashboardModule, ModuleManifest, register

from . import models  # noqa: F401
from .mcp import TOOLS
from .router import router
from .service import summary

MANIFEST = ModuleManifest(
    key="example",
    name="Example",
    icon="🧩",
    version="0.1.0",
    description="Blueprint module. Copy me with scripts/new_module.py.",
)

module = register(
    DashboardModule(manifest=MANIFEST, router=router, summary_fn=summary, mcp_tools=TOOLS)
)
