"""Central configuration. 12-factor: everything overridable via env (HESTIA_*)."""

from __future__ import annotations

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HESTIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- core ---
    app_name: str = "Hestia"
    environment: str = "dev"  # dev | prod
    database_url: str = "sqlite:///./hestia.db"

    # Which modules are active. Empty -> built-in defaults (see app/modules/__init__.py).
    # Example: HESTIA_ENABLED_MODULES=dogs,subscriptions
    # NoDecode: stop pydantic-settings from json.loads()-ing the env var so the
    # validator below can split plain CSV. See docs/FAILURES.md F-003.
    enabled_modules: Annotated[list[str], NoDecode] = []

    # --- multi-tenant (household) ---
    # Single-household deployments resolve agent/MCP writes to this household.
    default_household_id: int = 1

    # --- auth ---
    # dev    -> no auth, acts as the dev user (local only)
    # proxy  -> trust identity headers injected by Authentik / reverse proxy
    # strict -> only Bearer agent tokens are accepted for the API
    auth_mode: str = "dev"
    dev_user_email: str = "roberto@casa.local"
    dev_user_name: str = "Roberto"

    proxy_user_header: str = "X-Authentik-Username"
    proxy_email_header: str = "X-Authentik-Email"

    # A single master agent token (quick path for Hermes). Additional, revocable
    # per-agent tokens live in the api_tokens table. Leave empty to disable.
    agent_token: str | None = None

    # --- mcp (agent surface) ---
    mcp_transport: str = "stdio"  # stdio | sse | streamable-http
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8765

    # MCP auth + audit. Only meaningful for HTTP transports (i.e. when the MCP
    # server is exposed, e.g. behind a Cloudflare Tunnel). stdio is a local pipe
    # and bypasses these entirely.
    #   require_auth -> reject MCP calls without a valid agent bearer token
    #   audit        -> append every tool call to a JSON-Lines log (rotated)
    mcp_require_auth: bool = True
    mcp_audit_enabled: bool = True
    mcp_audit_log_path: str = "./hestia-mcp-audit.log"
    mcp_audit_max_bytes: int = 5_000_000
    mcp_audit_backups: int = 5

    # --- integrations (placeholders; real creds wired per-integration later) ---
    google_client_id: str | None = None
    google_client_secret: str | None = None
    bring_email: str | None = None
    bring_password: str | None = None

    @field_validator("enabled_modules", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        """Accept a comma-separated string from the env (HESTIA_ENABLED_MODULES=dogs,subscriptions).

        pydantic-settings otherwise tries to json.loads() list-typed env vars, which
        breaks on plain CSV. See docs/FAILURES.md F-003.
        """
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


settings = Settings()
