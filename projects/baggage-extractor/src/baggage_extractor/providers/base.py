from collections.abc import Mapping
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
class StructuredOutputSpec:
    name: str
    description: str
    json_schema: Mapping[str, object]
    strict: bool = True


@dataclass(frozen=True, slots=True)
class ModelRequest:
    messages: tuple[ChatMessage, ...]
    temperature: float = 0.0
    max_output_tokens: int | None = None
    structured_output: StructuredOutputSpec | None = None


@dataclass(frozen=True, slots=True)
class ModelResponse:
    content: str
    model: str
    request_id: str | None = None


class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
