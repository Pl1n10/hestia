# Decisions

Numbered, append-only architecture decision records. Each says what we chose and
why the alternatives lost. Supersede rather than edit.

---

## D-001 — Name: "hestia"

Hestia is the Greek goddess of the hearth and home — the warm centre of the
household. Fits the existing mythological naming (argus, hermes, delphi, nexus)
and reads as "the home" without being literal. Codename only; rename freely.

---

## D-002 — The service layer is the single source of truth

**Decision.** Every module exposes a `service.py` of plain functions over a
`Session`. The REST router, the MCP tools, and any future surface (Alexa) are
**thin adapters** that call those functions. No business logic lives in a router
or a tool.

**Why.** The whole product promise is "fillable by an agent *and* by a human,
always in sync." If the REST path and the agent path had separate logic they
would drift the day someone fixes a bug in one and not the other. A single
service layer makes drift structurally impossible: there is exactly one code
path to the data.

**Consequences.** Adding behaviour means editing `service.py` first. Routers stay
boring (validate → call service → serialize). MCP tools open their own session
(they run in a separate process) but call the identical functions.

**Rejected.** "Fat router, MCP calls REST over HTTP." Adds a network hop, a
second serialization layer, and couples the agent to the web app's uptime.

---

## D-003 — SQLite + WAL as the default store

**Decision.** SQLite with `journal_mode=WAL` and `foreign_keys=ON`, via a
connection-level pragma listener. SQLAlchemy 2.0 style (`DeclarativeBase`,
`Mapped`, `mapped_column`).

**Why.** A two-person household dashboard has tiny data and runs on the homelab.
SQLite is zero-ops, file-backed (trivial to back up via the existing homelab
jobs), and WAL gives enough read/write concurrency for one API process plus one
MCP process. Postgres would be operational weight with no payoff at this scale.

**Consequences.** `database_url` is configurable, so moving to Postgres later is a
URL change plus a driver — the ORM code does not change. Foreign keys are
enforced (off by default in SQLite), which already caught a missing-household bug
in tests.

---

## D-004 — Multi-tenancy via Household

**Decision.** The unit of tenancy is the **Household**. `User` and every module
row carry a `household_id`; all queries are scoped by it. Roberto + partner are
two `User`s in one `Household`.

**Why.** "Multi-user, one shared dashboard" is the literal requirement. Scoping by
household (not by user) means both people see and write the same data, while the
model still supports more than one household if this ever runs for someone else.

**Consequences.** `core_models.ApiToken.household_id` is a real FK to
`households`; module tables use a plain indexed `household_id` (scoping, not a
cross-module FK, to keep modules independent). Agent/MCP writes resolve to
`settings.default_household_id`.

---

## D-005 — Three auth modes, Authentik in front for humans

**Decision.** `auth_mode` ∈ {`dev`, `proxy`, `strict`}.
- `dev` — no auth, acts as the configured dev user. **Local only.**
- `proxy` — trust identity headers injected by Authentik (`X-Authentik-Username`
  / `-Email`); users are auto-provisioned into the household on first sight.
- `strict` — only `Authorization: Bearer <token>` is accepted.

Agents authenticate with a bearer token in every mode: either the env master
`agent_token` (quick path for Hermes) or a revocable row in `api_tokens`. Only
the **SHA-256 hash** is stored; the env token is compared with
`hmac.compare_digest` (constant time). A presented-but-invalid bearer does **not**
fall through to dev/proxy.

**Why.** Humans already authenticate at the homelab edge (Authentik behind
Cloudflare Tunnel); re-implementing login here would duplicate that and be worse.
Agents need a credential that is independent of a human session and individually
revocable. Hashing + constant-time compare mirrors the argus token pattern.

**Consequences.** In production the app trusts the proxy and never sees a
password. Tokens are unrecoverable after issue (hash-only), so `seed --token`
prints once.

---

## D-006 — The MCP server reflects over the module registry

**Decision.** `app/mcp/server.py` does not hard-code tools. It calls
`load_enabled()`, collects every module's `mcp_tools`, and registers them on a
`FastMCP` instance. Run it as its own process next to the API.

**Why.** The agent surface should grow automatically as modules are added. Writing
a new module already means writing its `mcp.py`; reflection means there is no
second place to wire it in. One registry, two readers (the app factory and the
MCP server).

**Consequences.** A module is "agent-ready" the moment it is enabled. Transport is
configurable (`stdio` for local, `streamable-http`/`sse` behind a Cloudflare
Tunnel for Hermes). MCP tools each open their own DB session because the server is
a separate process from the API.

---

## D-007 — Money is Numeric(10,2) + Decimal, never float

**Decision.** Subscription amounts are stored as `Numeric(10,2)`. All cost
arithmetic uses `Decimal` with explicit `quantize(0.01, ROUND_HALF_UP)`. Public
surfaces (REST/MCP JSON) expose `float` at the boundary only.

**Why.** Float arithmetic on money drifts (`0.1 + 0.2`). A monthly-cost rollup
that sums weekly/monthly/quarterly/yearly subscriptions compounds that error.
Decimal keeps it exact; the cycle-normalisation factors are Decimal too. See
FAILURES F-001.

**Consequences.** The generalisation to vehicles/utilities (bollo, assicurazione,
bollette) inherits correct money handling for free, since they reuse this shape.

---

## D-008 — Hestia's MCP is its own connector, separate from devbox-bridge

**Decision.** Even though Hestia will run on the same devbox as `devbox-bridge`,
its MCP surface is a **separate process, port, Cloudflare hostname, connector,
and token**. Hestia's tools are not merged into devbox-bridge.

**Why.** `devbox-bridge` is a *privileged operator* surface — it exposes
`run_command`, `write_file`, `git_push` on the box (hence its hardening, command
allowlists, and audit). Hestia is a *low-privilege domain* surface — log a dog
walk, add a subscription. Folding Hestia's tools into devbox-bridge would put
household actions behind the same token/connection that can run shell commands,
widening Hestia's blast radius along the exact boundary devbox-bridge was built
to protect, and coupling two unrelated lifecycles in one privileged process.
Hestia's tools also come from a runtime registry (D-006), so they *want* their
own server that grows with modules, not manual re-registration elsewhere.

**Consequences.** What gets reused is the **deployment pattern**, not the server:
same FastMCP + HTTP stack, same Cloudflare Tunnel daemon, same auth/audit shape
(this repo lifts the bearer + audit-log approach). Two connectors on claude.ai,
each independently revocable. Hestia MCP binds 8766 (devbox-bridge owns 8765).

---

## D-009 — MCP auth reuses the REST resolver, via pure-ASGI middleware

**Decision.** The MCP HTTP transport is gated by a bearer-auth middleware that
calls the **same** `resolve_principal` the REST API uses, accepting a request
only if it resolves to an **agent** (env master token or a hashed, revocable
`api_tokens` row). The middleware is pure ASGI, not Starlette's
`BaseHTTPMiddleware`.

**Why.** One identity code path for both surfaces keeps D-002's "no drift"
property across the agent transport too: tokens are minted, hashed, and revoked
in one place. Pure ASGI is required because `BaseHTTPMiddleware` buffers
responses and would break the streamable-http / SSE event stream (FAILURES
F-005). Humans/dev/proxy identities are never accepted on the MCP port — it is an
agent-only door. `stdio` is a local pipe and bypasses auth entirely.

**Consequences.** `mcp_require_auth` defaults on; an exposed MCP with no token
configured fails closed. Health paths are public so systemd/uptime can probe.

---

## D-010 — Every MCP tool call is audited

**Decision.** Tool handlers are wrapped at registration with a signature-
preserving audit wrapper that appends one JSON object per call (tool, principal,
household, redacted args, status, duration) to a rotated JSON-Lines log.

**Why.** The agent writes to the home unattended; "what did Hermes change" needs
a durable, structured trail — the same reason devbox-bridge audits. Wrapping at
the single registration chokepoint (D-006) means no per-tool boilerplate and no
way to add a tool that escapes auditing. Signature preservation
(`functools.wraps` + explicit `__signature__`) is mandatory or FastMCP loses the
tool's input schema (FAILURES F-006).

**Consequences.** Sensitive arg keys are redacted defensively. Auditing never
raises into the tool call. The principal comes from a ContextVar the auth
middleware sets per request.

---

## D-011 — Feature requests are a module, not a side channel

**Decision.** The way the agent asks for the dashboard *itself* to grow is a
first-class module (`feature_requests`), built on the same contract as every
other vertical: a `service.py`, a REST router, MCP tools, and a summary card.
Hermes files a request with `feature_requests_add`; it lands in the same DB the
humans see; Claude Code reads the open queue and flips the status
(`new → in_progress → done | rejected`) as it builds. It ships in `AVAILABLE`
(enabled by default) because every deployment wants this loop.

**Why.** The request was "let Hermes ask for new features so Claude Code can
build them." Modelling that as a bespoke endpoint or an external tracker would
break the one architectural promise (D-002): the agent path and the human path
would diverge, and the request queue would live outside the dashboard the
requests are *about*. As a module it inherits household scoping, the audit log
(D-010), agent auth (D-005/D-009), and a dashboard card — for free — and it
doubles as the canonical worked example of the managed-entity-with-lifecycle
shape (like `subscriptions`, minus the money).

**Consequences.** The feature backlog is queryable over REST and MCP and visible
on the home view. Claude Code's intake is `GET /api/modules/feature_requests/requests?open_only=true`
(or the `feature_requests_list` tool). `resolution` carries the implementer's
note / PR link / rejection reason. Unknown statuses are ignored rather than
written, so the lifecycle can't be corrupted from the agent surface.

---

## OPEN — Absorb vs. integrate the existing sgambamento app

There is already a live FastAPI + SQLite app for Milka's sgambamenti at
`sgambamento.robertonovara.me`. The `dogs` module here owns its own data, which
**overlaps**. Two paths:

- **Absorb** — make `dogs` the system of record, migrate the existing data in,
  retire the standalone app. Cleanest long-term; costs a migration + a cutover.
- **Integrate** — keep the standalone app authoritative and have `dogs` proxy /
  sync from it (treat it like an integration with a `DogActivitySource`
  capability). No migration; two systems to keep alive.

Not decided. The `dogs` module is built as owning-its-data so either path stays
open: absorbing is a data import, integrating means swapping the service's
backend for a client. Decide before seeding real Milka data in production.
