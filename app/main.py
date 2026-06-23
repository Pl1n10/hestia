"""Hestia API - application factory.

Wiring:
* enabled module routers  -> /api/modules/<key>/...
* system routes           -> /api/health, /api/me, /api/modules, /api/dashboard,
                             /api/integrations
* the dashboard shell     -> GET /
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import __version__
from app.auth import Principal
from app.db import init_db
from app.deps import current_principal, get_db
from app.modules import load_enabled
from app.modules.base import ModuleSummary, get_registry
from app.settings import settings

_STATIC = Path(__file__).parent / "web" / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    load_enabled()  # ensure registry is populated even if init order changes
    import app.integrations  # noqa: F401  (registers integrations)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in prod (Authentik sits in front anyway)
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- mount enabled module routers ---
    for module in load_enabled().values():
        app.include_router(
            module.router,
            prefix=f"/api/modules/{module.key}",
            tags=[module.manifest.name],
        )

    app.include_router(_system_router())

    # --- frontend shell ---
    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(_STATIC / "index.html")

    return app


def _system_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["system"])

    @router.get("/health")
    def health():
        return {"status": "ok", "version": __version__, "app": settings.app_name}

    @router.get("/me")
    def me(p: Principal = Depends(current_principal)):
        return {
            "kind": p.kind,
            "display_name": p.display_name,
            "household_id": p.household_id,
            "user_id": p.user_id,
        }

    @router.get("/modules")
    def modules(_p: Principal = Depends(current_principal)):
        return [
            {
                "key": m.manifest.key,
                "name": m.manifest.name,
                "icon": m.manifest.icon,
                "version": m.manifest.version,
                "description": m.manifest.description,
                "tools": [t.name for t in m.mcp_tools],
            }
            for m in get_registry().values()
        ]

    @router.get("/dashboard", response_model=list[ModuleSummary])
    def dashboard(
        p: Principal = Depends(current_principal), db: Session = Depends(get_db)
    ):
        cards: list[ModuleSummary] = []
        for m in get_registry().values():
            try:
                cards.append(m.summary_fn(db, p.household_id))
            except Exception as exc:  # one bad module must not break the home view
                cards.append(
                    ModuleSummary(
                        key=m.key,
                        name=m.manifest.name,
                        icon="⚠️",
                        headline=f"Errore modulo: {exc}",
                    )
                )
        return cards

    @router.get("/integrations")
    def integrations(_p: Principal = Depends(current_principal)):
        from app.integrations import get_registry as integ_registry

        return [
            {**integ.health(), "name": integ.manifest.name, "description": integ.manifest.description}
            for integ in integ_registry().values()
        ]

    return router


app = create_app()
