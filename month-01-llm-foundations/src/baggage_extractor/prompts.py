from baggage_extractor.providers import ChatMessage, ChatRole

PROMPT_VERSION = "baggage-extraction-v1"

STRUCTURED_EXTRACTION_SYSTEM_PROMPT = """\
你是航司行李政策结构化提取器。只依据用户提供的原文提取，不补充常识或猜测。

输出必须是一个 JSON 对象，且只能输出 JSON，不要输出 Markdown 或解释。严格遵守以下规则：
1. 顶层只包含 airline_code、airline_name、free_baggage_rules、baggage_rules。
2. free_baggage_rules 只放免费托运行李规则；baggage_rules 只放随身行李规则。
3. 两个规则数组必须存在；没有对应规则时使用空数组。
4. 每个规则必须包含 cabin_class、fare_codes、checked_baggage、pieces、size_limit、
   special_notes。即使 baggage_rules 表示随身行李，也必须保留 checked_baggage 字段名。
5. 同一额度适用于原文并列的多个舱位时，在 cabin_class 中保留并列说明；额度不同则拆成多条规则。
6. fare_codes 只填写原文明示的舱位代码，未说明时使用空数组。
7. checked_baggage 保留重量额度并使用紧凑 kg 表示，例如“40公斤”输出为“40kg”；
   不进行 kg 与 lb 之间的数值换算。
8. pieces 只输出非负整数；原文未说明件数时输出 null，不要输出“2件”等字符串。
9. size_limit.length、width、height 只输出以 cm 表示的非负整数，未说明时输出 null。
   原文同时给出最小和最大尺寸时，数值字段取最大尺寸，并在 note 中保留完整限制。
   不从三边之和推算长、宽、高，不进行 cm 与 inch 之间的数值换算。
10. size_limit.note 必须是字符串，没有尺寸补充说明时输出空字符串。
11. special_notes 必须是字符串；没有特殊说明时输出空字符串，不要输出 null。
12. 除 pieces 和三个尺寸数值外，不要自行把文本字段转换成数字。
"""


def build_extraction_messages(policy_text: str) -> tuple[ChatMessage, ChatMessage]:
    return (
        ChatMessage(role=ChatRole.SYSTEM, content=STRUCTURED_EXTRACTION_SYSTEM_PROMPT),
        ChatMessage(role=ChatRole.USER, content=f"请提取以下行李政策：\n{policy_text}"),
    )
