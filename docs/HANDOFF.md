# Handoff

Where this is, and what the next session should pick up.

## What you're inheriting

A working modular skeleton: core + tenancy + auth + module registry + two
reference modules (`dogs`, `subscriptions`) + the `feature_requests` meta module
(Hermes files requests, Claude Code builds them — DECISIONS D-011) + an MCP
server that reflects the registry + a single-file dashboard. 88 tests green. See
`docs/STATE.md` for the full built/stubbed breakdown.

**Claude Code intake:** read the open feature queue before planning work —
`GET /api/modules/feature_requests/requests?open_only=true` (or the
`feature_requests_list` MCP tool). Flip status to `in_progress` when you start
and `done`/`rejected` (with a `resolution` note) when you finish.

## Start here

```bash
make install
make seed            # add --token to mint a Hermes token (printed once)
make run             # http://127.0.0.1:8000
make test
```

Read `CLAUDE.md` for the architecture in one screen, then `docs/FAILURES.md`
before proposing anything.

## Highest-value next steps, in order

1. **Wire Google Calendar** (`app/integrations/google_calendar.py`). It's the most
   useful real integration and the template for the rest. OAuth wiring plan is in
   the class docstring; needs `HESTIA_GOOGLE_CLIENT_ID` / `_SECRET`. Keep it behind
   the `CalendarSource` protocol.
2. **Decide the sgambamento question** (DECISIONS "OPEN"): absorb the existing
   app's data into `dogs`, or integrate it as a `DogActivitySource`. Decide before
   real Milka data lands in prod.
3. **Add the next module** with `python -m scripts.new_module vehicles --name
   Veicoli --icon 🚗`. Vehicles/utilities follow the `subscriptions` shape
   (recurring + due dates); hardware/licenses too.
4. **Point Hermes at the MCP server.** Run `HESTIA_MCP_TRANSPORT=streamable-http
   python -m app.mcp.server` behind a Cloudflare Tunnel (e.g.
   `hestia-mcp.robertonovara.me`), mint a token with `seed --token`, register it
   in Hermes.
5. **Production posture.** Put the API behind Authentik (`HESTIA_AUTH_MODE=proxy`),
   tighten CORS off `*`, and back up the SQLite file with the existing homelab job.

## Conventions to keep

- New behaviour → `service.py` first, then surfaces (D-002).
- Money → Decimal (D-007). Queries → always `household_id`-scoped.
- New module → copy `_template` via `new_module.py`; write its `summary()` and
  `mcp.py`; enable via `HESTIA_ENABLED_MODULES`.
- Every module ships a `summary()`, a router, and (usually) MCP tools, or it's not
  pulling its weight.

## Gotchas already paid for (don't relearn)

- List env vars need `NoDecode` + a CSV validator (FAILURES F-003).
- Test routing with `TestClient`, not `app.routes` (FAILURES F-004).
- `api_tokens.household_id` is a real FK — the household row must exist before you
  insert a token (surfaced in tests).
