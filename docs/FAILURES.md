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

---

## F-007 — A summary card whose item list disagrees with its own stat count

**Tried.** Building the `subscriptions` card's `items` preview from
`upcoming(days=30)` — only the subscriptions renewing in the next 30 days — while
the card's `Attive` stat counted **all** active subscriptions.

**Why it failed.** A real, active subscription with a far-future renewal (a yearly
Amazon Prime renewing in 6 months) or no `next_renewal` at all was **counted in
the stats but absent from the list**. To the user it looked like the agent had
*failed to add it* — they re-ran `subscriptions_add` repeatedly, creating
duplicates (see F-008). The card silently contradicted itself: "5 active" over a
list of 3. This wasted a real debugging round-trip; Hermes had been writing
correctly all along.

**Do instead.** A card's item list must be a faithful view of the same set its
headline stat counts. `summary()` lists **every active** subscription (soonest
renewal first, undated last); the 30-day `upcoming` window is used **only** for
the headline ("prossimo rinnovo…"), never to filter what the card shows. Guarded
by `test_summary_lists_every_active_sub_not_just_upcoming`. General rule in
ANTIPATTERNS ("a card whose items and stats disagree").

---

## F-008 — A write capability in `service.py` + REST but not on the MCP surface

**Tried.** `subscriptions` shipped `update`/`delete` in the service layer **and**
as REST `PATCH`/`DELETE`, but its `mcp.py` exposed only `subscriptions_add`
(plus reads). The agent literally had no way to *edit* a subscription.

**Why it failed.** When Hermes needed to correct a subscription (fix a renewal
date), the only write tool it had was "add" — so it added a second row. Result:
duplicate "Amazon Prime" entries. The capability existed everywhere a *human*
could reach it and nowhere the *agent* could, which is exactly the divergence
D-002 exists to prevent — just in the surface-coverage direction rather than the
logic direction.

**Do instead.** When `service.py` gains a write that an agent could plausibly
need, expose it on **every** surface that needs it in the same change — REST
*and* MCP. Don't leave the agent with a partial verb set (add-only) that forces
it into duplicates. Added `subscriptions_update` + `subscriptions_delete` MCP
tools (the service already had them). General rule in ANTIPATTERNS ("surface
capability drift").

---

## F-009 — A stray relative-path SQLite DB when the env isn't loaded

**Tried.** Running a Hestia process (a `seed`, a `python -c`, an `hestia-mcp`
invocation) from a directory **without** the project `.env` / `HESTIA_DATABASE_URL`
loaded.

**Why it failed.** With no `HESTIA_DATABASE_URL`, the default is a **relative**
SQLite path, so SQLite happily creates a fresh empty `hestia.db` in whatever the
CWD happens to be (a stray `/home/hypn0/hestia.db` appeared this way). The API and
the agent then read/write **different files** and silently diverge — writes "land"
but never show up. We found one stale empty copy and removed it.

**Do instead.** Always run Hestia commands from the repo root **with the env
loaded**, or with `HESTIA_DATABASE_URL` set to the **absolute** path (the `.env`
does this, and D-012 already mandates absolute paths in the Hermes MCP `env` for
the same reason). In the systemd deploy the `EnvironmentFile` guarantees it; the
trap is manual/co-located runs. If subscriptions "added by Hermes" don't appear,
**check you're not looking at two different DB files** before suspecting the code.

---

## F-010 — Shipping a tool but Hermes still can't see it (stale stdio MCP subprocess)

**Tried.** Adding/renaming an MCP tool in `app/` (here: `subscriptions_delete`,
then `hestia_help`), confirming a fresh `hestia-mcp` exposes it, and assuming
Hermes now has it.

**Why it failed — twice.** Hermes reaches Hestia over a **stdio** MCP pipe
(D-012): the `hermes-gateway` service spawns `hestia-mcp` as a child subprocess
**once, at gateway startup**, and that subprocess holds the tool list for its
whole lifetime. The editable install means the *code on disk* is current, but the
**running subprocess is not** — it had been up ~10h, predating the change. So
Hermes kept filing feature requests for `subscriptions_remove` (#3, then #5) for a
capability (`subscriptions_delete`) that already existed: it literally couldn't
see the tool. The on-disk code, the tests, and a freshly-spawned server were all
correct; only the long-lived child was stale.

**Do instead.** After changing Hestia's MCP surface (any new/renamed tool),
**restart the process that owns the subprocess** so it respawns with the new
code: `systemctl --user restart hermes-gateway` (restarting the *API* service is
**not** enough — that's a different process; the agent's pipe is the gateway's
child). To diagnose before suspecting code: `ps -o etimes,lstart,cmd -C python |
grep hestia-mcp` — if its start time predates your edit, it's stale. The
`hestia_help` tool can't help here either until the very subprocess that would
serve it is restarted.
