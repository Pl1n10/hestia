# State

Snapshot of what exists, what's a stub, and what's not started. Update when the
shape changes.

## Built and tested

- **Core**: settings (env-driven), DB layer (SQLite + WAL + FK pragmas), session
  management, app factory.
- **Tenancy**: Household / User / ApiToken models, household-scoped queries.
- **Auth**: `Principal` + `resolve_principal` across `dev` / `proxy` / `strict`;
  bearer agent tokens (env master + hashed DB tokens, constant-time compare).
- **Module contract + registry**: `DashboardModule`, manifest, summary/stat/item
  models, in-process registry, discovery via `AVAILABLE` + `load_enabled()`.
- **Module `dogs`** (reference shape A — append-mostly log): models, schemas,
  service (+ `summary`), REST router, 3 MCP tools.
- **Module `subscriptions`** (reference shape B — managed recurring + money):
  models, schemas, service with Decimal cost rollup, REST router (full CRUD),
  6 MCP tools (`list` / `add` / `update` / `delete` / `monthly_cost` /
  `upcoming`). The summary card lists **every active** subscription, soonest
  renewal first (the 30-day window is headline-only — FAILURES F-007).
- **Module `feature_requests`** (managed entity + lifecycle — the *meta* module):
  how Hermes asks for the dashboard to grow. Status machine
  (`new → in_progress → done | rejected`), priority, `requested_by`,
  `resolution`; service, schemas, REST router (CRUD + PATCH), 3 MCP tools
  (`add` / `list` / `set_status`), summary card. Enabled by default. See
  DECISIONS D-011.
- **Module `_template`**: copy-me blueprint (not loaded).
- **MCP server**: reflects the registry, registers every tool on FastMCP,
  configurable transport. HTTP transports are gated by a pure-ASGI **bearer-auth
  middleware** (reuses `resolve_principal`, agent-only) and every tool call is
  written to a rotated JSON-Lines **audit log**; a public `/healthz` route lets
  systemd probe without a token.
- **Deploy**: `deploy/` ships hardened systemd units (`hestia-api`,
  `hestia-mcp`), a cloudflared ingress snippet, an idempotent `install.sh` +
  `uninstall.sh`, and `docs/DEPLOY.md` — a phase-by-phase runbook for Claude Code
  on the devbox (coexists with devbox-bridge: separate port 8766, connector, and
  token).
- **System API**: `/api/health`, `/api/me`, `/api/modules`, `/api/dashboard`
  (aggregates summaries; one broken module yields an error card, not a 500),
  `/api/integrations`.
- **Frontend**: single-file dashboard shell (`/`) that renders the dashboard,
  module cards by severity, and integration status.
- **Scripts**: `seed.py` (idempotent; `--token` mints a one-time agent token),
  `new_module.py` (clones `_template`, patches `AVAILABLE`).
- **Tests**: 92 passing (settings/F-003, registry, auth, dashboard + resilience,
  dogs, subscriptions/Decimal + card-coverage + update/delete via MCP,
  feature_requests/lifecycle, integrations/protocol, MCP, scaffolder).

## Stubbed — protocol defined, sync raises `NotImplementedError`

- **Google Calendar** (`CalendarSource`): OAuth wiring + `list_events`. Plan is in
  the class docstring. Needs `google_client_id` / `_secret`.
- **Gmail** (`MailSource`): surface "important mail" → feed into subscriptions.
- **Bring** (`ShoppingList`): unofficial API; behind the capability protocol so it
  can be swapped (see FAILURES F-002). `FakeShoppingList` works today.

## Not started (roadmap modules — each is one of the two proven shapes)

- **vehicles** — bollo, oil/filters, insurance (recurring-with-due-date → like
  subscriptions).
- **utilities / bollette** — utility bills, agent-extracted from mail
  (recurring + amounts).
- **hardware** — PC + phone inventory, warranty/licence dates.
- **licenses** — software licences with renewal dates.
- **shopping** — a real list behind the `ShoppingList` protocol (native or Bring).

## Known TODO / loose ends

- **Autonomous build loop** for `feature_requests`: today it's an inbox (Hermes
  files, a human runs Claude Code to build). Automating it — a watcher that wakes
  headless Claude Code on a new request, PR-gated — is deferred. Guardrails are
  already specified in DECISIONS "PLANNED".
- Wire at least one real integration (Calendar is the highest-value first one).
- Decide the sgambamento app question (DECISIONS "OPEN").
- Tighten CORS in production (currently `*`; Authentik sits in front).
- The cost endpoint returns floats at the boundary; that's intentional (D-007).
- **Doubled REST path segment**: module routers mount at `/api/modules/<key>`
  *and* declare routes as `/<key>/...`, so the live path is
  `/api/modules/subscriptions/subscriptions/{id}`. Cosmetic but confusing; see
  DECISIONS "OPEN — doubled module route segment". Not yet fixed.

## Integration mode

- **Co-located with Hermes (same host, one user):** Hermes spawns the Hestia
  **stdio** MCP server as a subprocess (DECISIONS D-012). Only the API runs as a
  long-lived service; `hestia-mcp.service` (HTTP) stays off.
- **Remote / hardened multi-user:** the HTTP MCP transport behind a Cloudflare
  Tunnel (D-008/D-009) — the `deploy/` path. Use this only when crossing a host
  or trust boundary.
- The human web UI is **read-only** (only `GET`s). All writes go through the
  service layer via the REST API or Hermes's MCP tools, never the browser.
