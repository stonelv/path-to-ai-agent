from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True, slots=True)
class ModelRequest:
    messages: tuple[ChatMessage, ...]
    temperature: float = 0.0
    max_output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ModelResponse:
    content: str
    model: str
    request_id: str | None = None


class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
