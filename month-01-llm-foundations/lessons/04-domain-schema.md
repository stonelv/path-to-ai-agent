# 第 4 课：领域 Schema 与确定性校验

上一课：[异步与错误处理](./03-error-handling.md) · [课程索引](./README.md) · 下一课：[结构化提取闭环](./05-structured-extraction.md)

> **状态：规划中。** 本课已有实施任务和验收标准，但仓库中尚无对应的领域模型、测试或参考实现。
> 完成实现并通过发布检查后，才能将状态改为“可学习”。

## 目标与前置

建议 2～3 小时。需要完成第 3 课，理解 Pydantic `BaseModel`、枚举、可空字段和字段校验。

本课只处理确定性的领域建模，不调用真实模型。完成后应能：

- 用 Pydantic 表达一条或多条行李规则。
- 区分“未说明”“明确为零”和“没有可提取规则”。
- 拒绝负数、未知枚举和没有额度的无效规则。
- 生成供下一课模型调用使用的 JSON Schema。

## 为什么先做 Schema

模型返回 JSON 不代表结果可供业务使用。在发起结构化模型请求前，需要先确定：

1. 业务允许哪些字段和值。
2. 缺失信息如何表达。
3. 哪些错误必须由程序拒绝。
4. 同一文本中的不同适用条件如何拆分。

本课的测试全部针对普通 Python 对象，不依赖 Prompt、模型供应商或网络。

## 必做范围

只支持：

- 中文文本。
- 托运行李。
- 成人和婴儿。
- 经济舱。
- 件数、单件重量、总重量和三边之和。
- 航司、始发地和目的地缺失时返回 `null`。
- 一段文本产生零条、一条或多条规则。

暂不支持：

- 英文和单位换算。
- 儿童、会员等级和票价品牌。
- 多舱位复杂组合。
- 手提行李和随身物品。
- 模型自报置信度。

超出范围的输入不能被静默解释成普通成功结果。下一课使用 `warnings` 明确报告暂不支持或无法可靠表达的信息。

## 动手任务

### 1. 创建文件

新增：

```text
src/baggage_extractor/models.py
tests/test_models.py
docs/schema.md
```

`docs/schema.md` 记录字段含义、可空规则、示例和当前不支持范围，不复制整份自动生成的 JSON Schema。

### 2. 定义最小领域模型

建议层次：

```text
ExtractionResult
├── schema_version
├── rules: list[BaggageRule]
└── warnings: list[str]

BaggageRule
├── airline
├── origin
├── destination
├── cabin_class
├── passenger_type
├── baggage_type
├── allowance
├── conditions
└── source_text

BaggageAllowance
├── piece_count
├── weight_per_piece_kg
├── total_weight_kg
└── linear_dimensions_cm
```

枚举先限制为当前范围：

- `PassengerType.ADULT`
- `PassengerType.INFANT`
- `CabinClass.ECONOMY`
- `BaggageType.CHECKED`

不要为了未来需求提前加入大量枚举值。新增能力时再同步扩展 Schema、测试和评估数据。

### 3. 明确字段语义

| 表达 | 含义 |
| --- | --- |
| `null` | 原文没有说明该字段 |
| `0` | 原文明示额度为零 |
| `rules: []` | 文本中没有可提取的行李额度 |
| `warnings` | 输入存在超范围、歧义或无法可靠表达的信息 |
| `source_text` | 直接支持当前规则的最小原文证据 |

`source_text` 不是整篇输入的机械复制。下一课还需验证它确实来自输入文本，防止模型生成不存在的证据。

数值必须支持非负约束。若需要表达小数重量，优先考虑 `Decimal`；选择具体类型后，在 `docs/schema.md` 说明序列化行为。

### 4. 添加确定性校验

至少保证：

- 件数、重量和三边之和不能为负。
- `source_text` 不能为空白字符串。
- 每条规则至少有一个额度字段不为 `null`。
- 未知枚举值校验失败。
- 不用 `0` 自动替换缺失数据。
- 空规则列表是合法结果。

不要添加未经业务证实的约束，例如“计件制一定不能同时出现总重量”。

### 5. 编写测试

在 `tests/test_models.py` 覆盖：

1. 合法的单件 23 kg 规则。
2. 合法的总重量 20 kg 规则。
3. 缺少航司时接受 `null`。
4. 明确零额度时保留 `0`。
5. 件数为负时失败。
6. 重量为负时失败。
7. 未知旅客类型时失败。
8. 空白 `source_text` 时失败。
9. 所有额度字段均为 `null` 时失败。
10. 成人与婴儿两条规则可以同时存在。
11. 无相关政策时接受空规则列表。

断言具体字段和错误位置，不要只断言“抛出了某个异常”。

### 6. 生成并检查 JSON Schema

使用 Pydantic 生成 `ExtractionResult` 的 JSON Schema，并用测试确认：

- Schema 可以序列化为 JSON。
- 必填字段和可空字段符合设计。
- 枚举只包含当前支持值。
- 顶层允许多条规则和空规则列表。
- Schema 不包含 `confidence`。

JSON Schema 是下一课请求模型的契约，但模型服务接受该 Schema 后，程序仍需再次执行 Pydantic 校验。

## 运行与预期

以下命令需在实现完成后运行。当前规划状态下，`tests/test_models.py` 尚不存在。

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

<details>
<summary>实现提示</summary>

- 复用项目当前的 Pydantic 2，不增加新的建模依赖。
- 可以用模型级校验器检查“至少存在一个额度字段”。
- 注意 Python 中 `0` 是假值，不能用简单的 `any(values)` 判断字段是否存在；应判断字段是否为 `None`。
- 领域模型不要读取配置，也不要依赖具体 Provider。
- `schema_version` 用显式固定值，后续不兼容变更时再升级。

</details>

## 常见问题

- **把 `0` 当成缺失：**会丢失“明确没有免费额度”的业务含义。
- **Schema 一次覆盖全部航司规则：**会让第一课领域建模变成长期需求分析，阻塞首个闭环。
- **只验证 JSON 类型：**数值是整数不代表它允许为负，也不代表一条规则包含有效额度。
- **在模型层检查证据是否属于输入：**领域模型本身不知道完整输入，这项校验应由下一课的提取服务执行。

## 验收与交付

- [ ] `models.py` 不依赖模型供应商或网络。
- [ ] 所有正常、边界和失败测试通过。
- [ ] 能解释 `null`、`0` 和空规则列表的区别。
- [ ] 能解释 JSON Schema 校验与业务校验的区别。
- [ ] `docs/schema.md` 记录当前范围和字段语义。
- [ ] 完整 pytest 与 Ruff 没有因新增模型失败。

建议独立提交：

```text
Add baggage domain schema
```

完成本课后进入[第 5 课](./05-structured-extraction.md)，将 Schema 接入模型请求并实现提取服务。
