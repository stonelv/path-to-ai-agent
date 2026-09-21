from baggage_extractor.models import ExtractionResult
from baggage_extractor.providers import ModelProvider


async def extract(policy_text: str, provider: ModelProvider) -> ExtractionResult:
    """Implement the lesson 02 extraction contract without delegating to BaggageExtractor."""
    raise NotImplementedError("Complete lesson 02 before running the learner acceptance tests.")
