# Antipatterns

Easy mistakes that quietly erode the architecture. If a change looks like one of
these, stop.

**Logic in a router or an MCP tool.** The moment a surface contains a calculation,
a filter, or a write rule that the other surfaces don't share, the app and the
agent can diverge. All logic goes in `service.py`; surfaces only validate,
delegate, and serialize. (DECISIONS D-002.)

**A module reaching into another module's tables.** Modules are independent
verticals. Cross-module reads go through the other module's `service.py`, never by
importing its models and querying them. Module `household_id` is a scoping column,
not a cross-module FK, on purpose.

**Float for money.** Any cents arithmetic with `float` is a bug, even if it looks
right in one example. `Numeric` + `Decimal` + `quantize`. (FAILURES F-001.)

**Depending on a vendor instead of a capability.** "Call the Bring API here" couples
the feature to an unofficial endpoint. Depend on the `ShoppingList` /
`CalendarSource` / `MailSource` protocol; let an integration implement it.
(FAILURES F-002.)

**Hard-coding a tool list in the MCP server.** Tools come from the registry by
reflection. Adding a module's tool means writing its `mcp.py`, nothing in the
server. (DECISIONS D-006.)

**Skipping `household_id` in a query.** Every module query filters by
`household_id`. A query without it leaks across households the day a second one
exists. There is no global "all rows" read in normal code paths.

**Trusting a bearer that didn't validate.** `resolve_principal` returns `None` for
a presented-but-invalid bearer — it must **not** fall through to dev/proxy. Don't
"helpfully" relax that.

**Letting one module crash the home.** `/api/dashboard` wraps each module's
`summary()` in try/except and emits an error card. Don't replace that with a bare
loop that 500s the whole page because one module threw.

**Storing a token in the clear.** Only the SHA-256 hash of an `ApiToken` is stored.
Never log or persist the plaintext; it's shown once at issue.

**Introspecting `app.routes` to test routing.** Included routers are lazy objects
here; the paths won't show. Test with `TestClient` behaviourally. (FAILURES F-004.)

**Auto-loading `_template`.** It's a blueprint, not a module. It stays out of
`AVAILABLE` and out of discovery; `new_module.py` copies it.
