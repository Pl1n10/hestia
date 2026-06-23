"""The resolved identity of a caller. Either an *agent* (Hermes, future Alexa
skill) holding a bearer token, or a *human* identified by the reverse proxy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Principal:
    kind: str  # "agent" | "human"
    display_name: str
    household_id: int
    user_id: int | None = None
    token_id: int | None = None

    @property
    def is_agent(self) -> bool:
        return self.kind == "agent"

    @property
    def is_human(self) -> bool:
        return self.kind == "human"
