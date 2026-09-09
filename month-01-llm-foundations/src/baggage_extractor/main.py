import asyncio

from baggage_extractor.config import get_settings
from baggage_extractor.providers import (
    ChatMessage,
    ChatRole,
    ModelRequest,
    OpenAICompatibleProvider,
)
from baggage_extractor.telemetry import TimedModelResponse, generate_with_timing

SAMPLE_POLICY = (
    "北京至东京经济舱成人旅客可免费托运1件行李，每件不超过23公斤，"
    "三边之和不得超过158厘米。"
)


async def run_model_experiment() -> TimedModelResponse:
    settings = get_settings()
    provider = OpenAICompatibleProvider(settings)
    request = ModelRequest(
        messages=(
            ChatMessage(
                role=ChatRole.SYSTEM,
                content=(
                    "你是航司行李政策分析助手。只根据用户提供的原文回答，"
                    "不要补充原文未说明的信息。"
                ),
            ),
            ChatMessage(
                role=ChatRole.USER,
                content=f"请提取以下行李政策的关键信息：\n{SAMPLE_POLICY}",
            ),
        ),
        temperature=0.0,
        max_output_tokens=300,
    )
    return await generate_with_timing(provider, request)


def main() -> None:
    result = asyncio.run(run_model_experiment())
    print(f"Started: {result.started_at.isoformat()}")
    print(f"Finished: {result.finished_at.isoformat()}")
    print(f"Latency: {result.latency_seconds:.3f} seconds")
    print(f"Model: {result.response.model}")
    print(f"Request ID: {result.response.request_id or 'not provided'}")
    print("Response:")
    print(result.response.content)


if __name__ == "__main__":
    main()
