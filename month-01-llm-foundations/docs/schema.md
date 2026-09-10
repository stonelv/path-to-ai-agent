# 行李额领域 Schema

本文件是[领域模型](../src/baggage_extractor/models.py)的字段语义与提取约定入口。自动生成的 JSON Schema
由 `ExtractionResult.model_json_schema()` 提供，不在这里保存副本，以免文档与代码漂移。
当前领域契约版本为 `baggage-result-v1`，真实评估报告会与 Prompt、数据和包版本一同记录它。

## 顶层结构

`ExtractionResult` 包含四个必填键：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `airline_code` | `string \| null` | 航司二字码、三字码或数据源使用的航司代码 |
| `airline_name` | `string \| null` | 航司名称 |
| `free_baggage_rules` | `FreeBaggageRule[]` | 免费托运行李规则 |
| `baggage_rules` | `CarryOnBaggageRule[]` | 随身行李规则 |

两个规则数组始终存在。没有对应政策时返回空数组，不能省略字段，也不能把两类规则合并。
航司信息未在输入原文中提供时保留为 `null`，不得猜测；当前提取器没有额外航司上下文参数。

## 规则结构

免费托运行李和随身行李使用相同的 JSON 字段，但在 Python 中分别使用
`FreeBaggageRule` 和 `CarryOnBaggageRule`，使调用方能在类型层区分两类规则。
这不保证模型把事实放入了正确数组；JSON 字段相同，放错位置仍可能通过结构校验。

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

公斤重量在提取时使用紧凑的 kg 表达，例如 `"40kg"` 或 `"每件不超过23kg"`，保留额度语义。
这是 Prompt 的提取约定，不是 Pydantic 自动归一化或 kg 格式校验。
件数和三个尺寸字段只接受非负整数或 `null`，拒绝布尔值、浮点数和数字字符串；明确零额度为 `0`，不是未知。
尺寸单位固定为 cm；单位换算、最大/最小值判断和原文证据核对不在领域模型中执行。

## 结构示例

以下为合成教学示例，不是真实航司政策。

输入：

```text
示例航空经济舱 Y、B、M 舱旅客可免费托运1件行李，每件不超过23公斤，
三边之和不超过158厘米；同一批旅客可携带1件随身行李，每件不超过5公斤，
尺寸不超过55×40×20厘米。
```

期望输出：

```json
{
  "airline_code": null,
  "airline_name": "示例航空",
  "free_baggage_rules": [
    {
      "cabin_class": "经济舱",
      "fare_codes": ["Y", "B", "M"],
      "checked_baggage": "每件不超过23kg",
      "pieces": 1,
      "size_limit": {
        "length": null,
        "width": null,
        "height": null,
        "note": "三边之和不超过158厘米"
      },
      "special_notes": ""
    }
  ],
  "baggage_rules": [
    {
      "cabin_class": "经济舱",
      "fare_codes": ["Y", "B", "M"],
      "checked_baggage": "每件不超过5kg",
      "pieces": 1,
      "size_limit": {
        "length": 55,
        "width": 40,
        "height": 20,
        "note": "尺寸不超过55×40×20厘米"
      },
      "special_notes": ""
    }
  ]
}
```

原文没有代码，所以 `airline_code` 为 `null`；两类行李都明确给出 1 件，因此 `pieces` 都是 `1`。
托运只给三边之和，不推算长宽高。说明文本保留限制语义，不要求模型逐字生成相同排版。

## 当前边界

领域模型校验结构、必填键、整数类型与非负约束、受约束文本是否为空白以及未知字段。它不会：

- 判断航司代码与名称是否匹配。
- 解析重量字符串中的数值。
- 换算单位或推算缺失尺寸。
- 判断舱位代码是否真实存在。
- 判断提取内容是否确实来自输入原文。
- 检测所有超范围条件、政策冲突或被放错类别的规则。

这些约束需要通过后续领域逻辑、归一化服务或固定评估分别验证。
当前提取器已实现结构校验，但尚未实现通用事实核对或超范围自动拒答。

## 提示词约定

上述提取约定由[版本化 Prompt](../src/baggage_extractor/prompts.py)表达，不在多个文档中保存提示词副本。
[提取器](../src/baggage_extractor/extractor.py)发送生成的严格 JSON Schema，
拒绝损坏 JSON、重复对象键和 `NaN` / `Infinity`，再执行 Pydantic 校验。
更改 Prompt 时应记录版本并进行相应回归；提示词仍不能替代事实质量评估。
