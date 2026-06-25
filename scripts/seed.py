"""Seed a usable household so the dashboard isn't empty on first run.

Idempotent-ish: if the default household already exists we leave it alone and
only (re)issue an agent token if you pass --token. Run with:

    python -m scripts.seed
    python -m scripts.seed --token        # also mint a fresh Hermes token

The plaintext agent token is printed exactly once. Only its SHA-256 hash is
stored (api_tokens table); there is no way to recover it later.
"""

from __future__ import annotations

import argparse
import secrets
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.auth.providers import hash_token
from app.core_models import ApiToken, Household, User
from app.db import SessionLocal, init_db
from app.modules import load_enabled
from app.settings import settings


def _get_or_create_household(db, name: str) -> Household:
    hh = db.get(Household, settings.default_household_id)
    if hh:
        return hh
    hh = Household(id=settings.default_household_id, name=name)
    db.add(hh)
    db.commit()
    db.refresh(hh)
    return hh


def _ensure_user(db, household_id: int, *, name: str, email: str, role: str) -> User:
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        return existing
    user = User(household_id=household_id, name=name, email=email, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _mint_token(db, household_id: int, name: str) -> str:
    plain = "hestia_" + secrets.token_urlsafe(32)
    db.add(
        ApiToken(
            household_id=household_id,
            name=name,
            token_hash=hash_token(plain),
            principal_name="hermes",
        )
    )
    db.commit()
    return plain


def seed(make_token: bool = False) -> None:
    # Make sure every enabled module's tables exist before we write to them.
    load_enabled()
    init_db()

    db = SessionLocal()
    try:
        hh = _get_or_create_household(db, "Casa Novara")
        print(f"household #{hh.id}: {hh.name}")

        roberto = _ensure_user(
            db, hh.id, name="Roberto", email="roberto@casa.local", role="owner"
        )
        # Placeholder for Roberto's partner — rename in the app, not invented here.
        compagna = _ensure_user(
            db, hh.id, name="Compagna", email="compagna@casa.local", role="member"
        )
        print(f"users: {roberto.name} (owner), {compagna.name} (member)")

        _seed_dogs(db, hh.id)
        _seed_subscriptions(db, hh.id)
        _seed_tiles(db, hh.id)

        if make_token:
            token = _mint_token(db, hh.id, "hermes-devbox")
            print("\n  agent token (shown once — store it in Hermes now):\n")
            print(f"    {token}\n")
            print("  use as:  Authorization: Bearer " + token)
        else:
            print("\n  (re-run with --token to mint a Hermes agent token)")
    finally:
        db.close()


def _seed_dogs(db, household_id: int) -> None:
    # Imported lazily so seeding only touches modules that are enabled.
    if "dogs" not in load_enabled():
        return
    from app.modules.dogs import service as dogs

    if dogs.list_dogs(db, household_id):
        return
    milka = dogs.create_dog(
        db, household_id, name="Milka", breed="Berger Picard", notes="Scruffy, instancabile."
    )
    now = datetime.now(timezone.utc)
    dogs.log_activity(
        db, household_id, milka.id, type="sgambamento",
        occurred_at=now - timedelta(hours=3), duration_min=40, logged_by="Roberto",
    )
    dogs.log_activity(
        db, household_id, milka.id, type="pappa",
        occurred_at=now - timedelta(hours=1), logged_by="Compagna",
    )
    print("  dogs: Milka + 2 attività")


def _seed_subscriptions(db, household_id: int) -> None:
    if "subscriptions" not in load_enabled():
        return
    from app.modules.subscriptions import service as subs

    if subs.list_subscriptions(db, household_id):
        return
    today = date.today()
    samples = [
        dict(name="Netflix", vendor="Netflix", amount=12.99, cycle="monthly",
             next_renewal=today + timedelta(days=9), category="streaming"),
        dict(name="Spotify Family", vendor="Spotify", amount=17.99, cycle="monthly",
             next_renewal=today + timedelta(days=21), category="musica"),
        dict(name="iCloud 200GB", vendor="Apple", amount=2.99, cycle="monthly",
             next_renewal=today + timedelta(days=3), category="cloud"),
        dict(name="Dominio robertonovara.me", vendor="Cloudflare", amount=10.0, cycle="yearly",
             next_renewal=today + timedelta(days=120), category="infra"),
    ]
    for s in samples:
        subs.create_subscription(db, household_id, **s)
    print(f"  subscriptions: {len(samples)} di esempio")


def _seed_tiles(db, household_id: int) -> None:
    if "tiles" not in load_enabled():
        return
    from app.modules.tiles import service as tiles

    if tiles.list_tiles(db, household_id, active_only=False):
        return
    samples = [
        dict(
            title="Manutenzione Cucina",
            body="Ultima manutenzione: 22 giugno 2026",
            color="green",
            next_check_at=date(2026, 9, 22),
        ),
        dict(
            title="Stato Impianti",
            body="Controllo impianto elettrico e idraulico.",
            color="blue",
            next_check_at=date.today() + timedelta(days=90),
        ),
    ]
    for s in samples:
        tiles.create_tile(db, household_id, **s)
    print(f"  tiles: {len(samples)} riquadri di esempio")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the default Hestia household.")
    parser.add_argument(
        "--token", action="store_true", help="also mint a one-time Hermes agent token"
    )
    args = parser.parse_args()
    seed(make_token=args.token)
