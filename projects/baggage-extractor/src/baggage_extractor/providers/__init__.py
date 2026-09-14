"""Model provider abstractions and implementations."""

from baggage_extractor.providers.base import (
    ChatMessage,
    ChatRole,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    StructuredOutputSpec,
)
from baggage_extractor.providers.errors import (
    AuthenticationError,
    InvalidRequestError,
    InvalidResponseError,
    ModelProviderError,
    ProviderConnectionError,
    ProviderTimeoutError,
    RateLimitError,
    ServerError,
)
from baggage_extractor.providers.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "ChatMessage",
    "ChatRole",
    "ModelProvider",
    "ModelRequest",
    "ModelResponse",
    "StructuredOutputSpec",
    "OpenAICompatibleProvider",
    "AuthenticationError",
    "InvalidRequestError",
    "InvalidResponseError",
    "ModelProviderError",
    "ProviderConnectionError",
    "ProviderTimeoutError",
    "RateLimitError",
    "ServerError",
]
