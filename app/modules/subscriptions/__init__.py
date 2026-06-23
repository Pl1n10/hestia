"""Subscriptions module: registers models + DashboardModule on import."""

from app.modules.base import DashboardModule, ModuleManifest, register

from . import models  # noqa: F401
from .mcp import TOOLS
from .router import router
from .service import summary

MANIFEST = ModuleManifest(
    key="subscriptions",
    name="Subscription",
    icon="💳",
    version="0.1.0",
    description="Monitoraggio costi ricorrenti e scadenze rinnovi.",
)

module = register(
    DashboardModule(
        manifest=MANIFEST,
        router=router,
        summary_fn=summary,
        mcp_tools=TOOLS,
    )
)
