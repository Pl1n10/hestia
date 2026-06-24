"""Veicoli module."""

from app.modules.base import DashboardModule, ModuleManifest, register

from . import models  # noqa: F401
from .mcp import TOOLS
from .router import router
from .service import summary

MANIFEST = ModuleManifest(
    key="vehicles",
    name="Veicoli",
    icon="🚗",
    version="0.1.0",
    description="Bollo, assicurazione e tagliandi per ogni veicolo di casa.",
)

module = register(
    DashboardModule(
        manifest=MANIFEST,
        router=router,
        summary_fn=summary,
        mcp_tools=TOOLS,
    )
)
