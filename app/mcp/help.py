"""A self-description tool for the agent.

Hermes only ever sees the MCP surface, never the repo. So the canonical "what
can I do here" reference can't be a markdown file it won't read — it has to be a
tool. ``hestia_help`` reflects the *same* module registry the server builds its
tools from (see DECISIONS D-006/D-013), so the catalogue can never drift from the
tools that actually exist. It also carries the house rules that keep the agent
from re-deriving capabilities it already has (the duplicate-Netflix lesson:
FAILURES F-007/F-008 — removing a subscription is ``subscriptions_delete``, not a
missing feature).
"""

from __future__ import annotations

from app.modules.base import McpTool

# House rules. Phrased as instructions to the agent, not prose about it.
GUIDANCE: list[str] = [
    "Everything you read or write here is the exact same data the humans see in "
    "the Hestia app — there is no separate agent copy. Act accordingly.",
    "Before adding anything, list what's already there (the *_list tools). To "
    "change an existing item use its *_update tool; to remove one use its "
    "*_delete tool. Never add a second entry to 'fix' a wrong one — that creates "
    "duplicates.",
    "subscriptions: subscriptions_add refuses a second active entry with the same "
    "name and returns {\"error\": \"duplicate\", ...}. When you see that, call "
    "subscriptions_update or subscriptions_delete on the existing id instead.",
    "If a capability is genuinely missing, file it with feature_requests_add — "
    "but check this help first: the tool you want may already exist under a "
    "different name (e.g. 'remove a subscription' is subscriptions_delete).",
]


def hestia_help() -> dict:
    """Describe everything you (the agent) can do in this household — call this first.

    Returns the house rules plus every available tool, grouped by area, straight
    from the live registry. Use it when you're unsure which tool to use, or
    before filing a feature request, so you don't ask for something that already
    exists.
    """
    # Imported lazily so this module has no import-time dependency on the loader.
    from app.modules import load_enabled

    areas = []
    for module in load_enabled().values():
        if not module.mcp_tools:
            continue
        areas.append(
            {
                "module": module.key,
                "name": module.manifest.name,
                "icon": module.manifest.icon,
                "tools": [
                    {"name": t.name, "description": t.description}
                    for t in module.mcp_tools
                ],
            }
        )

    return {
        "app": "Hestia",
        "summary": "Shared household dashboard. The tools below read and write the "
        "home's real data; the app and you stay in sync because you call the "
        "same code.",
        "guidance": GUIDANCE,
        "areas": areas,
    }


def build_help_tool() -> McpTool:
    return McpTool(
        "hestia_help",
        "List everything the agent can do here (tools + house rules). Call first if unsure.",
        hestia_help,
    )
