"""Projects module: tracks cross-project development activity.

Registers ORM models + DashboardModule on import.
"""

from app.modules.base import DashboardModule, ModuleManifest, register

from . import models  # noqa: F401  (registers ORM tables on Base.metadata)
from .mcp import TOOLS
from .router import router
from .service import summary

MANIFEST = ModuleManifest(
    key="projects",
    name="Progetti",
    icon="🗂️",
    version="0.1.0",
    description="Panoramica dei progetti in sviluppo: stato, ultima attività e link al repo.",
)

module = register(
    DashboardModule(
        manifest=MANIFEST,
        router=router,
        summary_fn=summary,
        mcp_tools=TOOLS,
    )
)
