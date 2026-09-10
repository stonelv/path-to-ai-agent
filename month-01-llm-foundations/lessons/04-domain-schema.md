# 第 4 课：最终行李额 Schema 与确定性校验

上一课：[异步与错误处理](./03-error-handling.md) · [课程索引](./README.md) · 下一课：[结构化提取闭环](./05-structured-extraction.md)

> **状态：可学习。** 本课已有领域模型、参考测试、Schema 文档和离线验收。

## 目标与前置

建议 2～3 小时。需要完成第 3 课，并理解 Pydantic `BaseModel`、嵌套模型、列表、
可空字段和字段校验。

本课只处理确定性的领域建模，不调用真实模型。完成后应能：

- 用固定结构区分免费托运行李和随身行李规则。
- 保留舱位说明、舱位代码、重量、件数、尺寸和特殊说明。
- 区分 `null`、空数组和允许为空的说明字段。
- 生成供下一课模型调用使用的 JSON Schema。

## 为什么先确定最终格式

模型返回 JSON 不代表结果可供业务使用。在发起结构化模型请求前，需要先固定：

1. 顶层必须包含哪些键。
2. 免费托运行李和随身行李如何分开。
3. 缺失字段如何表达。
4. 哪些格式错误必须由程序拒绝。

本课测试只针对普通 Python 对象，不依赖 Prompt、模型供应商或网络。

## 最终数据结构

```text
ExtractionResult
├── airline_code
├── airline_name
├── free_baggage_rules: list[FreeBaggageRule]
└── baggage_rules: list[CarryOnBaggageRule]

BaggageRule
├── cabin_class
├── fare_codes: list[str]
├── checked_baggage
├── pieces
├── size_limit: SizeLimit
└── special_notes

SizeLimit
├── length
├── width
├── height
└── note
```

`free_baggage_rules` 表示免费托运行李，`baggage_rules` 表示随身行李。
两类规则的 JSON 字段相同，但分别使用 `FreeBaggageRule` 和 `CarryOnBaggageRule`
类型，防止业务代码混用。

目标格式要求随身行李规则也使用 `checked_baggage` 字段名。实现必须保留这个外部契约，
不能因为名称看起来像托运行李就改名或改变其含义。

## 字段语义

| 表达 | 含义 |
| --- | --- |
| `null` | 输入没有说明该文本字段 |
| `fare_codes: []` | 没有可提取的舱位代码 |
| `free_baggage_rules: []` | 没有免费托运行李规则 |
| `baggage_rules: []` | 没有随身行李规则 |
| `note: ""` | 没有尺寸补充说明 |
| `special_notes: ""` | 没有特殊说明 |

所有目标键必须存在。可空字段未说明时显式返回 `null`，不能省略。
只有 `note` 和 `special_notes` 使用空字符串表达“没有说明”。

重量保留为紧凑的 kg 字符串，件数和尺寸使用非负整数。例如：

- `checked_baggage`: `"40kg"`
- `pieces`: `2`
- `length`: `55`
- `note`: `"每件行李尺寸不超过55×40×20cm"`

原文同时给出最小和最大尺寸时，长宽高记录最大尺寸，`note` 保留完整限制。

## 动手任务

### 1. 定义模型

阅读[领域模型](../src/baggage_extractor/models.py)，确认：

- 所有模型使用 `extra="forbid"` 拒绝未知字段。
- 件数和长宽高只接受非负整数或 `null`。
- `note` 和 `special_notes` 接受空字符串。
- `SizeLimit` 的四个键必填，三个尺寸值可以是 `null`，`note` 始终是字符串。
- 两个规则数组都必填且允许为空。
- 模型不读取配置，也不依赖 Provider 或网络。

### 2. 理解“必填但可空”

下面两种输入不同：

```json
{"airline_code": null}
```

表示键存在，但输入没有提供航司代码；省略 `airline_code` 则表示输出结构不完整，应校验失败。

同理，尺寸未知时仍需返回完整的 `size_limit`：

```json
{
  "length": null,
  "width": null,
  "height": null,
  "note": ""
}
```

### 3. 运行并阅读测试

[模型测试](../tests/test_models.py)覆盖：

1. 用户给出的东航完整免费托运行李和随身行李结果。
2. 顶层、规则和尺寸键与目标格式完全一致。
3. 两类规则解析为不同 Python 类型。
4. 多规则和多舱位代码。
5. 两类空规则列表。
6. 未知值使用 `null`。
7. 非法件数和尺寸失败。
8. 空白航司字段失败。
9. 空白舱位代码失败并报告准确位置。
10. 缺失顶层键和未知字段失败。
11. JSON Schema 的必填键、数组元素和整数约束。

### 4. 检查 JSON Schema

使用 `ExtractionResult.model_json_schema()` 生成契约，并确认：

- Schema 可序列化为 JSON。
- 顶层只有最终格式要求的四个字段。
- 四个顶层字段全部必填。
- 两个规则数组引用不同的规则类型。
- `SizeLimit` 的四个键全部必填，三个尺寸字段是非负整数或 `null`。
- 不再包含旧的 `schema_version`、`warnings` 或数值额度字段。

JSON Schema 是下一课请求模型的结构契约，程序收到模型结果后仍需再次执行 Pydantic 校验。

## 运行与预期

在项目目录执行：

Windows / PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_models.py
.\.venv\Scripts\python.exe -m ruff check .
```

macOS / Linux：

```bash
.venv/bin/python -m pytest tests/test_models.py
.venv/bin/python -m ruff check .
```

测试不需要 `.env`、API Key 或网络。

## 常见问题

- **把 `baggage_rules` 当成托运行李：**本项目明确约定它表示随身行李。
- **擅自重命名 `checked_baggage`：**这是目标外部契约的一部分，即使位于随身行李规则中也需保留。
- **所有缺失值都使用 `null`：**`note` 和 `special_notes` 按目标格式使用空字符串。
- **把重量转换成数字：**`checked_baggage` 需要保留 kg 单位和额度上下文。
- **把件数输出为 `"2件"`：**目标字段是整数，应输出 `2`。
- **省略未知尺寸键：**键必须存在，未知值填 `null`。

## 验收与交付

- [ ] `models.py` 不依赖模型供应商或网络。
- [ ] 输出键与最终目标格式一致。
- [ ] 免费托运行李和随身行李不会混用。
- [ ] 非法整数、缺失键、受约束空白文本和未知字段会校验失败。
- [ ] `docs/schema.md` 记录字段语义和当前边界。
- [ ] 完整 pytest 与 Ruff 没有因新模型失败。

完成后进入[第 5 课](./05-structured-extraction.md)，将最终 Schema 接入模型请求并实现提取服务。
