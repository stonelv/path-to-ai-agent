class ModelProviderError(ValueError):
    """Base error raised when a model provider request cannot succeed."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class AuthenticationError(ModelProviderError):
    pass


class RateLimitError(ModelProviderError):
    pass


class ServerError(ModelProviderError):
    pass


class InvalidRequestError(ModelProviderError):
    pass


class ProviderTimeoutError(ModelProviderError):
    pass


class ProviderConnectionError(ModelProviderError):
    pass


class InvalidResponseError(ModelProviderError):
    pass
