"""Named ADK graph for the same five steps as production `run_watch`.

Production HTTP and Scheduler call `run_watch`, not this SequentialAgent.
The required Google agent framework in prod is the GenAI SDK (vision, voice, plan).
"""

from __future__ import annotations

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.base_agent import BaseAgent

from kitchenwatch.settings import gemini_model
from kitchenwatch.watch import WATCH_STEPS


class RetrieveAgent(BaseAgent):
    """Loads the ledger and the 48h expiry window. No LLM."""

    def __init__(self) -> None:
        super().__init__(
            name="retrieve",
            description="Load shelf + items expiring within the horizon.",
        )


class TrustAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="trust",
            description="Fail-closed Python rules. Gemini does not vote.",
        )


class WriteAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="write",
            description="Insert one Google Calendar event.",
        )


class VerifyAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="verify",
            description="GET the calendar event. Missing event fails the job.",
        )


def build_watch_agent() -> SequentialAgent:
    plan = LlmAgent(
        name="plan",
        model=gemini_model(),
        description="Propose one cook from retrieve state only.",
        instruction=(
            "Propose one cook. reason_item_id must be expiring. "
            "uses may only cite shelf item_id values. Do not invent food."
        ),
    )
    return SequentialAgent(
        name="kitchenwatch_watch",
        description="retrieve → plan → trust → write → verify",
        sub_agents=[
            RetrieveAgent(),
            plan,
            TrustAgent(),
            WriteAgent(),
            VerifyAgent(),
        ],
    )


def graph_step_names() -> tuple[str, ...]:
    return WATCH_STEPS
