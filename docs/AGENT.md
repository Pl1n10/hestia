# The agent surface — what Hermes can do, and how it finds out

Hermes (and any future MCP-speaking agent) never sees this repo. It sees only the
MCP tools. So the canonical answer to "what can the agent do here" is a **tool**,
not this file — this file is for the humans maintaining it. See DECISIONS D-013.

## Discovery: `hestia_help`

The first tool the agent should reach for is `hestia_help`. It returns:

- **`guidance`** — the house rules (edit/remove instead of duplicating; everything
  it writes is the same data humans see; check here before filing a feature
  request).
- **`areas`** — every enabled module with its tools (name + description), generated
  by reflecting the live registry (`app/mcp/help.py`).

Because it reflects the same registry `collect_tools()` builds from, the catalogue
**cannot drift** from the tools that actually exist. Add a module, register its
tools, and it shows up in `hestia_help` automatically — no doc to update.

## The verb set per module

Every managed-entity module exposes the full set, so the agent never has to fake a
missing verb by adding a duplicate:

| Intent            | subscriptions tool        |
|-------------------|---------------------------|
| see what's there  | `subscriptions_list`      |
| add new           | `subscriptions_add`       |
| change existing   | `subscriptions_update`    |
| **remove**        | `subscriptions_delete`    |

> The trigger for all this: Hermes filed a request for a `subscriptions_remove`
> command that already existed as `subscriptions_delete`. The lesson isn't "add
> the missing tool" — it was already there — it's "make the agent able to
> *discover* its verbs." Hence `hestia_help`.

## Duplicate guard

`subscriptions_add` refuses a second **active** subscription with the same name
(case/space-insensitive) and answers with the existing id plus a hint to use
`subscriptions_update` / `subscriptions_delete`. Pass `allow_duplicate=True` only
when two separate entries are truly intended (e.g. two distinct accounts).
Inactive (cancelled) subs don't block re-adding. The guard lives in `service.py`
(`DuplicateSubscriptionError`), so the REST POST inherits it as a `409`. See
FAILURES F-007/F-008 for the duplicate-Netflix history this closes.

## When something is genuinely missing

Then — and only then — `feature_requests_add`. Claude Code reads the open queue
and builds it (D-011). But check `hestia_help` first: the capability you want may
already exist under a different name.
