# Hestia

A modular **household dashboard** designed to be filled by an agent (Hermes today,
an Alexa skill tomorrow) just as easily as by a human in the web app. One shared
home, two people, plus whatever automations write to it.

The point of this repo is the **skeleton**, not the feature set. Two reference
modules (`dogs`, `subscriptions`) prove the two shapes every future module will
take; everything else is wiring you copy.

## The one idea to hold in your head

Every surface is a thin adapter over a module's `service.py`.

```
REST router  ─┐
MCP tool     ─┼─►  app/modules/<m>/service.py  ─►  ORM models  ─►  SQLite
(future)     ─┘         (the only place that touches the tables)
Alexa skill
```

The app and the agent are never out of sync because they call the **same**
functions. If you add behaviour, add it to `service.py` first, then expose it on
whichever surfaces need it. Never let a router or an MCP tool contain logic that
isn't also reachable by the others. See `docs/DECISIONS.md` D-002.

## Layout

```
app/
  settings.py          # all config via env (HESTIA_*)
  db.py                # engine, SQLite pragmas, Base, session
  core_models.py       # Household, User, ApiToken (the tenancy primitives)
  deps.py              # get_db, current_principal (FastAPI deps)
  auth/                # Principal + identity resolution (dev | proxy | strict)
  modules/
    base.py            # the module contract + in-process registry
    __init__.py        # discovery: AVAILABLE + load_enabled()
    dogs/              # reference module A: append-mostly activity log
    subscriptions/     # reference module B: managed recurring entities + money
    feature_requests/  # meta module: agent files requests, Claude Code builds them
    _template/         # copy-me blueprint (NOT loaded; used by new_module.py)
  integrations/        # capability protocols + stubs (Calendar, Mail, Shopping)
  mcp/server.py        # reflects the registry -> exposes every tool to agents
                       #   (HTTP transport: bearer auth + per-call audit log)
  main.py              # app factory; mounts modules; /api/dashboard aggregator
  web/static/          # single-file dashboard shell
scripts/               # seed.py, new_module.py
tests/                 # 70 tests; TDD, fresh DB per test
deploy/                # systemd units, cloudflared snippet, install/uninstall
docs/                  # DECISIONS / FAILURES / STATE / DEPLOY / VOCABULARY / ...
```

## Run it

```bash
make install           # venv + deps
make seed              # household + Milka + sample subs (+ --token for Hermes)
make run               # API + dashboard at http://127.0.0.1:8000
make mcp               # MCP server for Hermes (stdio by default)
make test
```

Deploy on the devbox (hardened systemd + cloudflared, for Claude Code to run):
see `docs/DEPLOY.md`.

## Read before you build

- `docs/FAILURES.md` — **read this first.** Approaches already tried and rejected.
  Re-proposing one wastes a round trip.
- `docs/DECISIONS.md` — why things are the way they are (numbered ADRs).
- `docs/VOCABULARY.md` — Household / Principal / Module / Integration / capability.
- `docs/ANTIPATTERNS.md` — the easy ways to break the architecture.

## Add a module

```bash
python -m scripts.new_module vehicles --name Veicoli --icon 🚗
```

Then model the data, write `service.py` (+ its `summary()`), and enable it with
`HESTIA_ENABLED_MODULES=...,vehicles`. The router and MCP tools follow the same
pattern as `dogs`.
