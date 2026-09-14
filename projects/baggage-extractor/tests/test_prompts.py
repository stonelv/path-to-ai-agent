from baggage_extractor.prompts import (
    PROMPT_VERSION,
    STRUCTURED_EXTRACTION_SYSTEM_PROMPT,
    build_extraction_messages,
)
from baggage_extractor.providers import ChatRole


def test_structured_prompt_defines_final_output_semantics() -> None:
    prompt = STRUCTURED_EXTRACTION_SYSTEM_PROMPT

    assert PROMPT_VERSION == "baggage-extraction-v2"
    assert "free_baggage_rules 只放免费托运行李规则" in prompt
    assert "baggage_rules 只放随身行李规则" in prompt
    assert "pieces 只输出非负整数" in prompt
    assert "数值字段取最大尺寸" in prompt
    assert "没有特殊说明时输出空字符串" in prompt
    assert "airline_code 或 airline_name 未说明时使用 null" in prompt
    assert "cabin_class 或 checked_baggage 未说明时使用 null" in prompt
    assert "只能输出 JSON" in prompt


def test_build_extraction_messages_keeps_policy_text_in_user_message() -> None:
    policy_text = "头等舱免费托运行李额为40公斤。"

    messages = build_extraction_messages(policy_text)

    assert messages[0].role is ChatRole.SYSTEM
    assert messages[0].content == STRUCTURED_EXTRACTION_SYSTEM_PROMPT
    assert messages[1].role is ChatRole.USER
    assert messages[1].content.endswith(policy_text)
