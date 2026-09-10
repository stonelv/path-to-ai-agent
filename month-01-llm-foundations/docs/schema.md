# 行李额领域 Schema

本文件说明 `baggage_extractor.models` 中的最终数据契约。自动生成的 JSON Schema
由 `ExtractionResult.model_json_schema()` 提供，不在这里保存副本，以免文档与代码漂移。

## 顶层结构

`ExtractionResult` 包含四个必填键：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `airline_code` | `string \| null` | 航司二字码、三字码或数据源使用的航司代码 |
| `airline_name` | `string \| null` | 航司名称 |
| `free_baggage_rules` | `FreeBaggageRule[]` | 免费托运行李规则 |
| `baggage_rules` | `CarryOnBaggageRule[]` | 随身行李规则 |

两个规则数组始终存在。没有对应政策时返回空数组，不能省略字段，也不能把两类规则合并。
航司信息未在输入或调用上下文中提供时保留为 `null`，不得猜测。

## 规则结构

免费托运行李和随身行李使用相同的 JSON 字段，但在 Python 中分别使用
`FreeBaggageRule` 和 `CarryOnBaggageRule`，使调用方能在类型层区分两类规则。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `cabin_class` | `string \| null` | 舱位说明，例如“经济舱” |
| `fare_codes` | `string[]` | 适用舱位代码，例如 `["Y", "B", "M"]` |
| `checked_baggage` | `string \| null` | 原文中的行李重量或额度说明 |
| `pieces` | `integer \| null` | 行李件数；原文未说明时为 `null` |
| `size_limit` | `SizeLimit` | 长、宽、高及尺寸补充说明 |
| `special_notes` | `string` | 重量限制、例外或其他特殊说明；没有时为 `""` |

`baggage_rules` 表示随身行李，但仍使用目标格式指定的 `checked_baggage` 字段名。
程序不会根据字段名称把它重新解释为托运行李；数组位置和 Python 类型决定规则类别。

`fare_codes` 始终是数组。原文未提供舱位代码时使用空数组，而不是放入空字符串。

## 尺寸结构

`SizeLimit` 包含四个必填键：

- `length`：以 cm 表示的非负整数长度，未说明时为 `null`。
- `width`：以 cm 表示的非负整数宽度，未说明时为 `null`。
- `height`：以 cm 表示的非负整数高度，未说明时为 `null`。
- `note`：尺寸限制的原文说明；没有补充说明时为 `""`。

原文同时给出最小和最大尺寸时，三个数值字段记录最大尺寸，`note` 保留完整限制。
领域模型不进行 cm/inch 换算，也不根据三边之和推算长、宽、高。

## 缺失值和文本校验

- 所有输出键都必须存在。
- 未说明的可空字段使用 `null`。
- `note` 和 `special_notes` 没有内容时使用空字符串。
- 其他受约束文本字段的空字符串或纯空白字符串会被校验拒绝。
- 没有免费托运行李或随身行李规则时，对应数组为 `[]`。
- 未定义字段会被拒绝，避免模型输出悄悄扩展契约。

重量使用字符串保留额度语义，并规范为紧凑的 kg 表达，例如 `"40kg"`。件数和三个尺寸字段
使用非负整数；尺寸单位固定为 cm。不同重量或尺寸单位之间的换算不在领域模型中进行。

## 结构示例

以下从东航期望结果中各展示一条免费托运行李和随身行李规则：

```json
{
  "airline_code": "MU",
  "airline_name": "中国东方航空",
  "free_baggage_rules": [
    {
      "cabin_class": "头等舱",
      "fare_codes": [],
      "checked_baggage": "40kg",
      "pieces": null,
      "size_limit": {
        "length": 40,
        "width": 60,
        "height": 100,
        "note": "每件行李尺寸不小于5×15×20cm且不超过40×60×100cm"
      },
      "special_notes": "每件重量不超过50kg"
    }
  ],
  "baggage_rules": [
    {
      "cabin_class": "头等舱",
      "fare_codes": [],
      "checked_baggage": "10kg",
      "pieces": 2,
      "size_limit": {
        "length": 55,
        "width": 40,
        "height": 20,
        "note": "每件行李尺寸不超过55×40×20cm"
      },
      "special_notes": ""
    }
  ]
}
```

## 当前边界

领域模型只校验结构、必填键、文本是否为空白以及未知字段。它不会：

- 判断航司代码与名称是否匹配。
- 解析重量字符串中的数值。
- 换算单位或推算缺失尺寸。
- 判断舱位代码是否真实存在。
- 判断提取内容是否确实来自输入原文。

这些约束需要在后续提取服务、归一化服务或固定评估集中分别实现。

## 提示词约定

版本化提示词位于 `baggage_extractor.prompts`。它要求模型：

- 只输出 JSON，并严格区分两个规则数组。
- 将公斤表示规范为 `kg`，但不进行 kg/lb 数值换算。
- 将件数输出为整数。
- 将明确以 cm 给出的长宽高输出为整数。
- 同时存在最小和最大尺寸时选择最大尺寸，并在 `note` 保留完整限制。
- 没有 `note` 或 `special_notes` 时输出空字符串。

提示词不能替代 JSON Schema 和 Pydantic 校验。结构化提取器会将本 Schema 作为严格的
Structured Output 请求发送，并在收到 JSON 正文后再次执行 Pydantic 校验。
