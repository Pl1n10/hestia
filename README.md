# 🔥 Hestia

A modular **household dashboard** built to be filled by an **agent** (Hermes
today, an Alexa skill tomorrow) just as easily as by a **human** in the web app.
One shared home, two people, plus whatever automations write to it.

Named for the Greek goddess of the hearth — the warm centre of the home.

> This repo is a living **skeleton**, not a finished product. Two reference
> modules prove the patterns; the rest is wiring you copy.

## The core idea

Every surface — REST, MCP tools, future Alexa — is a thin adapter over each
module's `service.py`. The app and the agent call the *same* functions, so they
can never drift out of sync.

```
REST router ─┐
MCP tool    ─┼─►  modules/<m>/service.py  ─►  models  ─►  SQLite
(Alexa…)    ─┘        (the only writer)
```

## Quickstart

```bash
make install          # venv + deps
make seed             # household + Milka + sample subscriptions
#   make seed TOKEN=1 # also mint a one-time Hermes agent token
make run              # API + dashboard -> http://127.0.0.1:8000
make mcp              # MCP server for agents (stdio)
make test             # 60 tests
```

Open `http://127.0.0.1:8000` for the dashboard, or `/docs` for the API.

## What's in the box

| Area | Status |
|------|--------|
| Core (config, DB, sessions, app factory) | ✅ |
| Tenancy (Household / User / ApiToken) | ✅ |
| Auth (dev / proxy / strict + bearer agent tokens) | ✅ |
| Module registry + contract | ✅ |
| `dogs` module (activity-log shape) | ✅ |
| `subscriptions` module (recurring + Decimal money) | ✅ |
| MCP server (reflects the registry) | ✅ |
| Dashboard frontend (single file) | ✅ |
| Google Calendar / Gmail / Bring | 🟡 stubs behind capability protocols |
| vehicles / utilities / hardware / licenses / shopping | ⬜ roadmap |

## Two module shapes (copy one)

- **`dogs`** — *append-mostly log*: events with a timestamp (sgambamenti, meals,
  vet). Use for anything you record as it happens.
- **`subscriptions`** — *managed recurring entities*: things with a cost and a
  due date, rolled up with exact Decimal math. Use for vehicles (bollo,
  insurance), utilities, licenses.

Add one:

```bash
python -m scripts.new_module vehicles --name Veicoli --icon 🚗
```

…then model the data, write its `service.py` + `summary()`, and enable it with
`HESTIA_ENABLED_MODULES=...,vehicles`.

## Agent (Hermes) integration

The MCP server reflects over the module registry, so every enabled module's tools
are exposed automatically. Run it with an HTTP transport behind a Cloudflare
Tunnel and point Hermes at it:

```bash
HESTIA_MCP_TRANSPORT=streamable-http HESTIA_MCP_PORT=8766 python -m app.mcp.server
```

The HTTP transport is gated by a bearer token (the connector sends
`Authorization: Bearer …`) and every tool call is written to a rotated
JSON-Lines audit log. Authenticate with a token from `make seed TOKEN=1` (only
its hash is stored). For a full devbox deploy — hardened systemd units,
cloudflared ingress, and a step-by-step runbook for Claude Code — see
**`docs/DEPLOY.md`** (it coexists with `devbox-bridge`: separate port, connector,
and token).

## Production posture

Humans authenticate at the homelab edge (Authentik behind Cloudflare Tunnel), so
run the API with `HESTIA_AUTH_MODE=proxy` and let the proxy inject identity.
Tighten CORS off `*`. Back up the SQLite file with your existing job. See
`docker-compose.yml` for the two-process layout.

## Docs

- `CLAUDE.md` — architecture in one screen.
- `docs/DECISIONS.md` — numbered ADRs (why things are this way).
- `docs/FAILURES.md` — approaches already rejected. **Read before proposing.**
- `docs/DEPLOY.md` — devbox deploy runbook (for Claude Code on the box).
- `docs/STATE.md` · `docs/VOCABULARY.md` · `docs/ANTIPATTERNS.md` · `docs/HANDOFF.md`

## Configuration

Everything is env-driven (`HESTIA_*`). See `.env.example` for the full list.

## License

MIT.
