import asyncio

from baggage_extractor.extractor import BaggageExtractor
from baggage_extractor.models import ExtractionResult


class ExtractionCapacityError(RuntimeError):
    pass


class ExtractionGate:
    def __init__(self, max_concurrent_requests: int, acquire_timeout_seconds: float) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._acquire_timeout_seconds = acquire_timeout_seconds

    async def extract(
        self,
        extractor: BaggageExtractor,
        policy_text: str,
    ) -> ExtractionResult:
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self._acquire_timeout_seconds,
            )
        except TimeoutError as error:
            raise ExtractionCapacityError(
                "The extraction service is at its concurrency limit."
            ) from error

        try:
            return await extractor.extract(policy_text)
        finally:
            self._semaphore.release()
