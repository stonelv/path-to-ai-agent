"""Provider-neutral public messages; never store private model reasoning."""

from dataclasses import dataclass
from typing import Literal, Protocol


class ProviderFailure(Exception):
    """An expected provider failure; adapters must not include sensitive diagnostics."""


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class ModelTurn:
    answer: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, object]


class Provider(Protocol):
    async def complete(
        self, messages: tuple[Message, ...], tools: tuple[ToolDefinition, ...]
    ) -> ModelTurn: ...
