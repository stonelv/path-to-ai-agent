import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from pydantic import ValidationError

from baggage_extractor import __version__
from baggage_extractor.api.dependencies import ExtractionGate
from baggage_extractor.api.errors import ServiceNotReadyError, install_exception_handlers
from baggage_extractor.api.models import (
    ErrorResponse,
    ExtractionRequest,
    ExtractionResponse,
    StatusResponse,
)
from baggage_extractor.config import Settings, get_settings
from baggage_extractor.extractor import BaggageExtractor
from baggage_extractor.providers import OpenAICompatibleProvider

LOGGER = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def _configuration_fields(error: ValidationError) -> tuple[str, ...]:
    return tuple(sorted({str(detail["loc"][0]) for detail in error.errors()}))


def create_app(
    *,
    extractor: BaggageExtractor | None = None,
    settings: Settings | None = None,
    max_concurrent_requests: int | None = None,
    acquire_timeout_seconds: float | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.extractor = extractor
        app.state.configuration_errors = ()

        selected_settings = settings
        if extractor is None and selected_settings is None:
            try:
                selected_settings = get_settings()
            except ValidationError as error:
                app.state.configuration_errors = _configuration_fields(error)

        concurrency = (
            max_concurrent_requests
            if max_concurrent_requests is not None
            else selected_settings.api_max_concurrent_requests
            if selected_settings
            else 4
        )
        acquire_timeout = (
            acquire_timeout_seconds
            if acquire_timeout_seconds is not None
            else selected_settings.api_acquire_timeout_seconds
            if selected_settings
            else 1
        )
        if concurrency < 1:
            raise ValueError("max_concurrent_requests must be at least 1.")
        if acquire_timeout <= 0:
            raise ValueError("acquire_timeout_seconds must be greater than 0.")
        app.state.extraction_gate = ExtractionGate(concurrency, acquire_timeout)

        if extractor is not None or selected_settings is None:
            yield
            return

        async with OpenAICompatibleProvider(selected_settings) as provider:
            app.state.extractor = BaggageExtractor(provider)
            yield

    app = FastAPI(
        title="Airline Baggage Extractor API",
        version=__version__,
        lifespan=lifespan,
    )
    install_exception_handlers(app)

    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        supplied_request_id = request.headers.get(REQUEST_ID_HEADER)
        request_id = (
            supplied_request_id
            if supplied_request_id and REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else str(uuid4())
        )
        request.state.request_id = request_id
        started = perf_counter()
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        LOGGER.info(
            "request completed method=%s path=%s status=%s duration_ms=%.3f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started) * 1000,
            request_id,
        )
        return response

    @app.get("/health", response_model=StatusResponse)
    async def health() -> StatusResponse:
        return StatusResponse(status="ok")

    @app.get(
        "/ready",
        response_model=StatusResponse,
        responses={503: {"model": ErrorResponse}},
    )
    async def ready(request: Request) -> StatusResponse:
        if request.app.state.extractor is None:
            raise ServiceNotReadyError
        return StatusResponse(status="ready")

    @app.post(
        "/v1/extractions",
        response_model=ExtractionResponse,
        responses={
            422: {"model": ErrorResponse},
            502: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    async def extract(
        payload: ExtractionRequest,
        request: Request,
    ) -> ExtractionResponse:
        active_extractor = request.app.state.extractor
        if active_extractor is None:
            raise ServiceNotReadyError
        result = await request.app.state.extraction_gate.extract(
            active_extractor,
            payload.text,
        )
        return ExtractionResponse(
            request_id=request.state.request_id,
            result=result,
        )

    return app


app = create_app()
