"""Model provider abstractions and implementations."""

from baggage_extractor.providers.base import (
    ChatMessage,
    ChatRole,
    ModelProvider,
    ModelRequest,
    ModelResponse,
)
from baggage_extractor.providers.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "ChatMessage",
    "ChatRole",
    "ModelProvider",
    "ModelRequest",
    "ModelResponse",
    "OpenAICompatibleProvider",
]
