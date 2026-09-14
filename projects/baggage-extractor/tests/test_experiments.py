from baggage_extractor.experiments import EXPERIMENT_CASES, SOURCE_URL
from baggage_extractor.main import run_model_experiment
from baggage_extractor.providers import ModelRequest, ModelResponse


def test_experiment_suite_covers_three_parameter_levels() -> None:
    assert len(EXPERIMENT_CASES) == 3
    assert [case.temperature for case in EXPERIMENT_CASES] == [0.0, 0.3, 0.7]
    assert [case.max_output_tokens for case in EXPERIMENT_CASES] == [1000, 1500, 2500]
    assert all(case.policy_text for case in EXPERIMENT_CASES)
    assert SOURCE_URL.startswith("https://webresource.airchina.com.cn/")


def test_experiment_case_builds_model_request() -> None:
    case = EXPERIMENT_CASES[0]

    request = case.to_model_request()

    assert request.temperature == case.temperature
    assert request.max_output_tokens == case.max_output_tokens
    assert request.messages[-1].content.endswith(case.policy_text)


async def test_experiment_accepts_provider_protocol() -> None:
    class StubProvider:
        async def generate(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(content=request.messages[-1].content, model="stub-model")

    case = EXPERIMENT_CASES[0]
    result = await run_model_experiment(StubProvider(), case)

    assert result.response.content.endswith(case.policy_text)
    assert result.response.model == "stub-model"
