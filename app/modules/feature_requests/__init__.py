"""Feature-requests module: registers ORM models + the DashboardModule on import.

The dashboard's *meta* module: how the agent asks for the dashboard to grow.
Hermes files requests over MCP; Claude Code reads the queue and builds them.
"""

from app.modules.base import DashboardModule, ModuleManifest, register

from . import models  # noqa: F401  (registers ORM tables on Base.metadata)
from .mcp import TOOLS
from .router import router
from .service import summary

MANIFEST = ModuleManifest(
    key="feature_requests",
    name="Richieste",
    icon="💡",
    version="0.1.0",
    description="Richieste di nuove funzionalità: Hermes le deposita, Claude Code le realizza.",
)

module = register(
    DashboardModule(
        manifest=MANIFEST,
        router=router,
        summary_fn=summary,
        mcp_tools=TOOLS,
    )
)
