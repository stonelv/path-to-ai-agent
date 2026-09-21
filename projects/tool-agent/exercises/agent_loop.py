"""Lesson 06: implement the loop, not another application or provider adapter."""

from tool_agent.agent import Limits, Result
from tool_agent.contracts import Provider
from tool_agent.tools import ToolRegistry


async def run_loop(
    provider: Provider, registry: ToolRegistry, request: str, limits: Limits
) -> Result:
    """Implement bounded model -> tool -> observation feedback.

    Reuse Message, ToolCall, validate_turn and SYSTEM_MESSAGE from the application.
    Reuse registry.prepare/execute, including whole-turn authorization preflight.
    Count model steps and started tool calls; return the existing Result type.
    Enforce ONE overall cooperative deadline, including provider and tool awaits.
    Map documented contract failures, but let unexpected programming errors escape.
    Events may be minimal; never store private reasoning.

    Do not call Agent.run or copy the application, tools, or demo provider here.
    Acceptance tests disable Agent.run unless --reference is explicitly selected.
    """
    raise NotImplementedError("Implement the bounded model/tool feedback loop.")
