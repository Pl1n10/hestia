"""Dogs module: registers ORM models + the DashboardModule on import."""

from app.modules.base import DashboardModule, ModuleManifest, register

from . import models  # noqa: F401  (registers ORM tables on Base.metadata)
from .mcp import TOOLS
from .router import router
from .service import summary

MANIFEST = ModuleManifest(
    key="dogs",
    name="Cani",
    icon="🐕",
    version="0.1.0",
    description="Registro sgambamenti e attività canine (passeggiate, pappe, vet).",
)

module = register(
    DashboardModule(
        manifest=MANIFEST,
        router=router,
        summary_fn=summary,
        mcp_tools=TOOLS,
    )
)
