# Failures

Approaches that were tried and **rejected**, with enough context that nobody
re-proposes them. This is the highest-value doc in the repo: read it before
suggesting any approach. An entry here is a closed door, not a TODO.

---

## F-001 — Money as float

**Tried.** Storing subscription amounts as `float` / `REAL` and summing them
directly for the monthly/yearly rollup.

**Why it failed.** Binary float can't represent most decimal cents exactly, so a
rollup that normalises weekly/monthly/quarterly/yearly costs accumulates error
and shows wrong totals (`€30.330000000000002/mese`).

**Do instead.** `Numeric(10,2)` in the DB, `Decimal` for all arithmetic, explicit
`quantize(Decimal("0.01"), ROUND_HALF_UP)`. Expose `float` only at the JSON
boundary. Codified in DECISIONS D-007 and guarded by `tests/test_subscriptions.py`.

---

## F-002 — Hard-depending on Bring for shopping

**Tried.** Designing the shopping feature directly against Bring's API as the
canonical backend.

**Why it failed (pre-emptively).** Bring has **no official API**; the usable
client (`bring-api` on PyPI) is reverse-engineered and can break on any vendor
change. Coupling the data model to it makes the whole shopping feature hostage to
an unofficial endpoint, and forecloses a nicer native list.

**Do instead.** Depend on a `ShoppingList` **capability protocol**
(`get_items` / `add_item` / `remove_item`), not on a vendor. `FakeShoppingList`
implements it in-memory today; Bring, a native list, or anything else can
implement it later without touching callers. The Bring class is a stub behind the
protocol. See `app/integrations/base.py` and DECISIONS D-002's "capability, not
vendor" spirit.

---

## F-003 — Letting pydantic-settings parse a list env var as JSON

**Tried.** Typing `enabled_modules: list[str]` and setting
`HESTIA_ENABLED_MODULES=dogs,subscriptions` in the environment.

**Why it failed.** pydantic-settings treats list-typed fields as "complex" and
runs `json.loads()` on the raw env value **before** any validator. A plain CSV
string isn't JSON, so the app crashed at import with
`SettingsError: error parsing value for field "enabled_modules"`. A
`field_validator(mode="before")` does **not** help — the JSON decode happens
first, in the env source.

**Do instead.** Annotate the field with `NoDecode` so pydantic-settings hands the
raw string to the validator, then split on commas:

```python
enabled_modules: Annotated[list[str], NoDecode] = []

@field_validator("enabled_modules", mode="before")
@classmethod
def _split_csv(cls, v):
    return [s.strip() for s in v.split(",") if s.strip()] if isinstance(v, str) else v
```

Guarded by `tests/test_settings.py`. (Was a real crash hit while scaffolding.)

---

## F-004 — Inspecting `app.routes` to confirm routers mounted

**Tried.** Asserting routes exist by reading `app.routes` and filtering for paths
starting with `/api`.

**Why it's misleading.** This FastAPI version (0.138) keeps included routers as
lazy `_IncludedRouter` objects in `app.routes` rather than flattening them into
`APIRoute` entries at include time. The `/api/...` paths therefore don't appear
when you iterate `app.routes`, even though the routes work perfectly.

**Do instead.** Verify routing behaviourally with `TestClient` (hit the endpoint
and check the response), never by introspecting the route list. All routing tests
use `TestClient`.

---

## F-005 — `BaseHTTPMiddleware` in front of the MCP stream

**Tried (considered).** Gating the MCP HTTP transport with a Starlette
`BaseHTTPMiddleware` subclass for the bearer check.

**Why it fails.** `BaseHTTPMiddleware` reads the downstream response through an
internal buffer, which breaks long-lived streaming responses —
`streamable-http` and SSE are exactly that. The MCP session would hang or drop.

**Do instead.** Use a **pure ASGI middleware** (`async def __call__(scope,
receive, send)`) that inspects `scope['headers']` and either passes the original
`receive`/`send` straight through (auth ok) or sends a 401 itself. No buffering,
no interference with the stream. See `app/mcp/auth.py`.

---

## F-006 — Wrapping a tool handler without preserving its signature

**Tried.** Wrapping each MCP tool handler (for auditing) with a plain
`def wrapper(*args, **kwargs)`.

**Why it fails.** FastMCP builds each tool's JSON input schema by introspecting
the handler's signature. A bare `*args, **kwargs` wrapper erases the typed
parameters, so the tool ships with an empty/loose schema and the agent can't see
its arguments.

**Do instead.** `functools.wraps(handler)` **and** explicitly copy the signature:
`wrapper.__signature__ = inspect.signature(handler)`. Verified: the wrapped
`subscriptions_add` still exposes `name` / `amount` / `cycle` with the correct
`required` set. See `app/mcp/audit.py` and `tests/test_mcp_hardening.py`.
