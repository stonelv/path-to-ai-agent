from baggage_extractor.experiments import EXPERIMENT_CASES, SOURCE_URL


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
