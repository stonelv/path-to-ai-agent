from dataclasses import dataclass

from baggage_extractor.providers import ChatMessage, ChatRole, ModelRequest

SOURCE_URL = (
    "https://webresource.airchina.com.cn/zh-CN/content/travel_info/"
    "preparing/luggage/check/tyxlgz/"
)

SYSTEM_PROMPT = (
    "你是航司行李政策分析助手。只根据用户提供的原文提取信息，不要补充原文未说明的"
    "内容。分别列出每条适用规则，并保留旅客类型、舱位、航线、会员条件、件数及重量。"
)


@dataclass(frozen=True, slots=True)
class ExperimentCase:
    name: str
    description: str
    policy_text: str
    temperature: float
    max_output_tokens: int

    def to_model_request(self) -> ModelRequest:
        return ModelRequest(
            messages=(
                ChatMessage(role=ChatRole.SYSTEM, content=SYSTEM_PROMPT),
                ChatMessage(
                    role=ChatRole.USER,
                    content=f"请提取以下行李政策的关键信息：\n{self.policy_text}",
                ),
            ),
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )


EXPERIMENT_CASES = (
    ExperimentCase(
        name="simple-low-temperature",
        description="简单单规则，低随机性和较短输出上限",
        policy_text=(
            "国航实际承运的中国境内计重制航班中，持成人或儿童客票的经济舱旅客，"
            "免费托运行李额为20公斤。"
        ),
        temperature=0.0,
        max_output_tokens=1000,
    ),
    ExperimentCase(
        name="multiple-rules-medium-temperature",
        description="多舱位和多旅客规则，中等随机性和输出上限",
        policy_text=(
            "国航实际承运的中国境内计重制航班中，持成人或儿童客票的旅客，"
            "头等舱免费托运行李额为40公斤，公务舱为30公斤，悦享经济舱、"
            "超级经济舱和经济舱均为20公斤。持婴儿客票的旅客，无论乘坐何种舱位，"
            "免费托运行李额为10公斤。"
        ),
        temperature=0.3,
        max_output_tokens=1500,
    ),
    ExperimentCase(
        name="membership-high-temperature",
        description="复杂会员和舱位条件，较高随机性和较长输出上限",
        policy_text=(
            "在国航实际承运的计件制航线上，凤凰知音终身白金卡、白金卡、金卡和"
            "银卡旅客乘坐头等舱或公务舱时，可额外免费托运1件不超过32公斤的行李；"
            "乘坐悦享经济舱、超级经济舱或经济舱时，可额外免费托运1件不超过23公斤"
            "的行李。星空联盟金卡旅客无论乘坐何种舱位，均可额外免费托运1件不超过"
            "23公斤的行李。"
        ),
        temperature=0.7,
        max_output_tokens=2500,
    ),
)
