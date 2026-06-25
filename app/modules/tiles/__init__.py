"""Tiles module: registers ORM models + the DashboardModule on import."""

from app.modules.base import DashboardModule, ModuleManifest, register

from . import models  # noqa: F401  (registers ORM tables on Base.metadata)
from .mcp import TOOLS
from .router import router
from .service import summary

MANIFEST = ModuleManifest(
    key="tiles",
    name="Riquadri",
    icon="📋",
    version="0.1.0",
    description="Riquadri personalizzabili del dashboard: promemoria, manutenzioni, note.",
)

module = register(
    DashboardModule(
        manifest=MANIFEST,
        router=router,
        summary_fn=summary,
        mcp_tools=TOOLS,
    )
)
