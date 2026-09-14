from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from baggage_extractor.api.dependencies import ExtractionCapacityError
from baggage_extractor.errors import (
    InvalidExtractionInputError,
    StructuredOutputParseError,
    StructuredOutputValidationError,
)
from baggage_extractor.providers import (
    AuthenticationError,
    InvalidRequestError,
    InvalidResponseError,
    ProviderConnectionError,
    ProviderTimeoutError,
    RateLimitError,
    ServerError,
)

ExceptionHandler = Callable[[Request, Exception], Awaitable[JSONResponse]]


class ServiceNotReadyError(RuntimeError):
    pass


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request.state.request_id,
            }
        },
    )


def _handler(status_code: int, code: str, message: str) -> ExceptionHandler:
    async def handle(request: Request, error: Exception) -> JSONResponse:
        return _error_response(
            request,
            status_code=status_code,
            code=code,
            message=message,
        )

    return handle


async def _request_validation_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        request,
        status_code=422,
        code="invalid_request",
        message="The request body did not match the API contract.",
    )


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _request_validation_handler)
    app.add_exception_handler(
        InvalidExtractionInputError,
        _handler(422, "invalid_input", "The policy text was invalid."),
    )
    app.add_exception_handler(
        ServiceNotReadyError,
        _handler(503, "service_not_ready", "The extraction service is not ready."),
    )
    app.add_exception_handler(
        ExtractionCapacityError,
        _handler(503, "capacity_exceeded", "The extraction service is busy."),
    )
    app.add_exception_handler(
        AuthenticationError,
        _handler(503, "model_authentication_failed", "Model authentication failed."),
    )
    app.add_exception_handler(
        RateLimitError,
        _handler(503, "model_rate_limited", "The model provider rate limit was exceeded."),
    )
    app.add_exception_handler(
        ProviderTimeoutError,
        _handler(504, "model_timeout", "The model request timed out."),
    )
    for error_type in (ProviderConnectionError, ServerError):
        app.add_exception_handler(
            error_type,
            _handler(502, "model_unavailable", "The model provider was unavailable."),
        )
    app.add_exception_handler(
        InvalidRequestError,
        _handler(502, "model_request_rejected", "The model provider rejected the request."),
    )
    for error_type in (
        InvalidResponseError,
        StructuredOutputParseError,
        StructuredOutputValidationError,
    ):
        app.add_exception_handler(
            error_type,
            _handler(502, "invalid_model_output", "The model returned an invalid result."),
        )
