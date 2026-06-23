"""Identity resolution.

Resolution order for an incoming request:

1. ``Authorization: Bearer <token>``
   * matches the env master ``agent_token`` (constant-time)  -> agent
   * else matches a row in ``api_tokens`` by SHA-256 hash    -> agent
2. ``auth_mode == "proxy"`` and a trusted identity header is present
   (injected by Authentik) -> human (user auto-provisioned in the household)
3. ``auth_mode == "dev"`` -> the configured dev user (LOCAL ONLY)
4. otherwise -> ``None`` (caller is unauthenticated; deps raise 401)

Tokens are never stored in the clear. Comparison of the env token uses
``hmac.compare_digest`` to keep it constant-time.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.principals import Principal
from app.core_models import ApiToken, Household, User
from app.settings import settings


def hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def verify_token(plain: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(plain), stored_hash)


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def _agent_from_token(token: str, db: Session) -> Principal | None:
    # 1) env master token (quick path for Hermes)
    if settings.agent_token and hmac.compare_digest(token, settings.agent_token):
        return Principal(
            kind="agent",
            display_name="hermes",
            household_id=settings.default_household_id,
        )
    # 2) revocable DB token, looked up by hash
    row = db.execute(
        select(ApiToken).where(ApiToken.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if row is not None:
        row.last_used_at = datetime.now(timezone.utc)
        db.commit()
        return Principal(
            kind="agent",
            display_name=row.principal_name,
            household_id=row.household_id,
            token_id=row.id,
        )
    return None


def _ensure_user(db: Session, email: str, name: str, household_id: int) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        # auto-provision into the household on first sight (proxy/dev convenience)
        if db.get(Household, household_id) is None:
            db.add(Household(id=household_id, name="Casa"))
            db.flush()
        user = User(household_id=household_id, name=name, email=email, role="member")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def resolve_principal(headers: dict[str, str], db: Session) -> Principal | None:
    # normalise header lookup (case-insensitive)
    lower = {k.lower(): v for k, v in headers.items()}

    token = _bearer(lower.get("authorization"))
    if token:
        agent = _agent_from_token(token, db)
        if agent is not None:
            return agent
        return None  # a bearer was presented but invalid -> do not fall through

    if settings.auth_mode == "proxy":
        username = lower.get(settings.proxy_user_header.lower())
        if username:
            email = lower.get(settings.proxy_email_header.lower()) or f"{username}@local"
            user = _ensure_user(db, email, username, settings.default_household_id)
            return Principal(
                kind="human",
                display_name=user.name,
                household_id=user.household_id,
                user_id=user.id,
            )
        return None

    if settings.auth_mode == "dev":
        user = _ensure_user(
            db, settings.dev_user_email, settings.dev_user_name, settings.default_household_id
        )
        return Principal(
            kind="human",
            display_name=user.name,
            household_id=user.household_id,
            user_id=user.id,
        )

    return None
