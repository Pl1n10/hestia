"""Structured audit log for the MCP surface.

Every agent tool call is appended as one JSON object per line (JSON Lines),
with size-based rotation. This is the "what did Hermes change in the house"
trail. Mirrors the audit approach proven in devbox-bridge.

Two pieces:
* ``audit_wrap(handler, name)`` — wraps a tool handler so each call is timed and
  recorded. It preserves the original signature so FastMCP still derives the
  correct JSON schema (see docs/FAILURES.md F-006).
* ``current_principal_name`` — a ContextVar the auth middleware sets per request
  so the log can attribute the call to the authenticated agent.
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable

from app.settings import settings

# Set by the auth middleware (HTTP transports). Defaults to "local" for stdio.
current_principal_name: ContextVar[str] = ContextVar("current_principal_name", default="local")

_REDACT = ("token", "password", "secret", "authorization", "api_key", "apikey")

_logger: logging.Logger | None = None
_logger_path: str | None = None


def _get_logger() -> logging.Logger | None:
    global _logger, _logger_path
    if not settings.mcp_audit_enabled:
        return None
    path = settings.mcp_audit_log_path
    if _logger is not None and _logger_path == path:
        return _logger

    logger = logging.getLogger("hestia.mcp.audit")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for h in list(logger.handlers):  # drop any stale handler (e.g. old path)
        h.close()
        logger.removeHandler(h)

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=settings.mcp_audit_max_bytes,
        backupCount=settings.mcp_audit_backups,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))  # we emit raw JSON
    logger.addHandler(handler)
    _logger = logger
    _logger_path = path
    return logger


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("***" if any(s in k.lower() for s in _REDACT) else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "…"
    return value


def record(event: dict) -> None:
    """Append one structured event. Never raises into the caller."""
    logger = _get_logger()
    if logger is None:
        return
    base = {"ts": datetime.now(timezone.utc).isoformat()}
    base.update(event)
    try:
        logger.info(json.dumps(base, default=str, ensure_ascii=False))
    except Exception:  # auditing must not break the tool call
        pass


def record_auth(*, ok: bool, principal: str | None, path: str, reason: str = "") -> None:
    record(
        {
            "event": "mcp_auth",
            "ok": ok,
            "principal": principal,
            "path": path,
            "reason": reason,
        }
    )


def audit_wrap(handler: Callable[..., Any], name: str) -> Callable[..., Any]:
    """Wrap a tool handler so each invocation is recorded.

    Signature-preserving: FastMCP introspects the wrapped function to build the
    tool's input schema, so we copy the original signature onto the wrapper.
    """

    @functools.wraps(handler)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        status = "ok"
        error = None
        try:
            result = handler(*args, **kwargs)
            # tools signal soft failures by returning {"error": ...}
            if isinstance(result, dict) and "error" in result:
                status = "error"
                error = str(result.get("error"))
            return result
        except Exception as exc:
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            record(
                {
                    "event": "mcp_tool_call",
                    "tool": name,
                    "principal": current_principal_name.get(),
                    "household_id": settings.default_household_id,
                    "args": _redact(kwargs),
                    "status": status,
                    "error": error,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )

    wrapper.__signature__ = inspect.signature(handler)  # keep the real schema
    return wrapper


def reset_for_tests() -> None:
    """Drop the cached logger so a test can point the path elsewhere."""
    global _logger, _logger_path
    logger = logging.getLogger("hestia.mcp.audit")
    for h in list(logger.handlers):
        h.close()
        logger.removeHandler(h)
    _logger = None
    _logger_path = None
