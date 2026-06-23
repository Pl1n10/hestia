# Handoff

Where this is, and what the next session should pick up.

## What you're inheriting

A working modular skeleton: core + tenancy + auth + module registry + two
reference modules (`dogs`, `subscriptions`) + the `feature_requests` meta module
(Hermes files requests, Claude Code builds them — DECISIONS D-011) + an MCP
server that reflects the registry + a single-file dashboard. 92 tests green. See
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
4. **Hermes integration.** *Co-located* (same host as Hermes): register Hestia as
   a **stdio** MCP server in Hermes — it spawns the `hestia-mcp` console script,
   with absolute `env` paths so it shares the API's SQLite file (DECISIONS D-012);
   no token/tunnel needed. *Remote*: `HESTIA_MCP_TRANSPORT=streamable-http` behind a
   Cloudflare Tunnel + `seed --token` (D-008/D-009).
5. **Production posture.** Put the API behind Authentik (`HESTIA_AUTH_MODE=proxy`),
   tighten CORS off `*`, and back up the SQLite file with the existing homelab job.

## Deferred (agreed, not now)

- **Autonomous build loop**: a watcher that wakes headless Claude Code on a new
  `feature_requests` entry and has it open a PR. Design + guardrails are pinned in
  DECISIONS "PLANNED" (isolated worktree, PR gate, no push to `main`, Hermes never
  writes code). Build when we choose to; until then the loop is human-triggered
  (see the intake note above).

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
- A summary card's `items` must show the same set its stats count — don't filter
  the list to a window the stat ignores, or real rows go invisible (FAILURES
  F-007).
- A new `service.py` write an agent could need goes on **REST and MCP** in the
  same change — add-only surfaces breed duplicates (FAILURES F-008).
- "Hermes wrote it but it's not there" → first suspect **two different DB files**,
  not the code: run with the absolute `HESTIA_DATABASE_URL` loaded (FAILURES
  F-009).
- The live module REST path has the key twice
  (`/api/modules/subscriptions/subscriptions/{id}`) — DECISIONS "OPEN — doubled
  module route segment".
