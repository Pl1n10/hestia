# Vocabulary

The words this codebase uses on purpose. Use them consistently; renaming a
concept mid-repo is how drift starts.

**Household** — the tenancy unit. One home. Holds Users and owns all module data
via `household_id`. Roberto + partner = two Users, one Household.

**User** — a human member of a Household (`owner` | `member`). Distinct from a
Principal: a User is a stored row; a Principal is who is making *this* request.

**Principal** — the resolved identity of the current caller. Either:
- an **agent** (Hermes, future Alexa) holding a bearer token, or
- a **human** identified by the reverse proxy (or the dev user locally).

Carries `household_id` so every handler can scope without re-deriving it.

**ApiToken** — a revocable credential for an agent. Only its SHA-256 hash is
stored; the plaintext is shown once at creation.

**Module** — a self-contained vertical (dogs, subscriptions, …) that owns its
tables and contributes one card to the dashboard. Declares a manifest, a REST
router, a `summary()` function, and zero or more MCP tools.

**Manifest** (`ModuleManifest`) — a module's identity card: `key`, `name`, `icon`,
`version`, `description`.

**Registry** — the in-process dict of enabled `DashboardModule`s. Populated by
importing module packages (`load_enabled()`); read by both the app factory and
the MCP server.

**Service layer** (`service.py`) — the only code allowed to touch a module's
tables. The single source of truth all surfaces call (DECISIONS D-002).

**Surface** — a way to reach the service layer: the REST router, an MCP tool, the
future Alexa skill. Surfaces are thin; logic lives in the service.

**Summary** (`ModuleSummary`) — what a module contributes to the home view: a
headline, some stat chips, a short list of items. Built by the module's
`summary(db, household_id)`.

**Integration** — a connection to an outside service (Calendar, Mail, Shopping).
Has a manifest, `is_configured()`, `health()`, and `sync()`.

**Capability** — a `Protocol` an integration can satisfy, independent of vendor:
`CalendarSource`, `MailSource`, `ShoppingList`. Callers depend on the capability,
not on Google or Bring (so vendors are swappable — FAILURES F-002).

**Auth mode** — `dev` (local, dev user) | `proxy` (trust Authentik headers) |
`strict` (bearer tokens only). Set via `HESTIA_AUTH_MODE`.

**sgambamento** — a dog outing / run-around (Milka's). The `dogs` activity type;
also the name of the pre-existing standalone app this may absorb or integrate.
