# 第 6 课：固定评估集、评分器与质量基线

上一课：[结构化提取闭环](./05-structured-extraction.md) · [课程索引](./README.md) · 下一课：[FastAPI 服务化](./07-fastapi-service.md)

## 目标与前置

建议 4～6 小时。需要完成第 5 课，理解 `ExtractionResult`、JSONL、测试分母和基本质量指标。
本课已有版本化合成数据、确定性评分器、离线示例、真实模型显式入口和参考测试。

完成后应能：

- 区分程序回归、评分器校准和真实模型质量评估。
- 建立有稳定 ID、来源、标签、版本和开发/留出划分的数据。
- 不依赖规则数组顺序比较嵌套输出。
- 分别报告错误值、遗漏规则、无依据规则、无依据字段和调用失败。
- 保留所有案例的分母，区分同集回归与独立留出验证，并在相同条件下比较 Prompt 或模型。

本课仍属于模块 02，不实现 FastAPI 或 Agent。课程数据是合成政策，不能用于真实旅客权益判断。

## 三种验证不能混淆

| 验证 | 输入 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| pytest | 人工构造的 expected / actual、Stub 与 Mock | 评分公式、加载失败和报告行为符合设计 | 真实模型质量 |
| 离线示例评分 | 固定数据 + 仓库保存的故意含错预测 | CLI 可复现，错误分类易于观察 | 任何模型达到该分数 |
| 真实模型评估 | 固定数据 → BaggageExtractor → 评分器 | 指定版本与运行条件下的质量和调用失败 | 全部航司、未来运行或生产表现 |

仓库不提交伪造的模型基线。只有实际执行真实模型评估后，报告才能作为对应模型与版本的基线。
新报告版本为 `1.1`，新增 `dataset_usage` 与 `dataset_limitations`；案例与预测文件仍使用 `1.0`。
字段由[显式用途声明](../evals/README.md#报告中的用途元信息)产生，不从文件名或分数推断独立性。
离线示例应标为 `development`，v1 原留出集应标为 `regression`，未登记的数据标为 `unverified`。

## 固定数据契约

阅读[数据说明](../evals/README.md)和
[评估模型](../src/baggage_extractor/evaluation/models.py)。
当前 `baggage-eval-v1` 包含 6 条开发案例与 6 条原留出案例，覆盖：

- 托运、随身行李和两者同时出现；
- 舱位代码、多规则拆分和相同额度条件；
- 未知件数、明确零额度、尺寸上下界与三边之和；
- 无关文本、缺失信息和防止常识补全。

数据量只够建立教学闭环，不具有统计代表性。开发集用于理解失败和改 Prompt。
当前 Prompt v2 已参考原留出集失败调优，因此 v1 原留出集仅用于教学与回归；
文件名和 split 标签保留历史含义，不能将它作为独立质量验收依据。
新留出集需使用未用于调优的案例，具体见[当前数据用途与限制](../evals/README.md#当前用途与限制)。

加载器会拒绝：

- 空文件、非法 JSONL 或不满足案例 Schema 的行；
- 重复案例 ID、混合数据版本或混合 split；
- 重复标签；
- 期望数组中重复的规则身份。

最后一项避免规则配对存在多个同样合理的答案。

## 确定性评分规则

### 规则如何配对

免费托运行李与随身行李只在各自数组中匹配。规则身份为：

```text
(cabin_class, sorted(fare_codes))
```

因此：

- 规则数组顺序不影响结果；
- 舱位代码顺序不影响结果，但重复代码仍会改变身份；
- 身份相同的候选中，选择字段匹配最多的一条；
- 没配对的期望规则是 `missing_rule`；
- 没配对的实际规则是 `unsupported_rule`。

如果舱位说明或代码本身错误，会表现为一条遗漏加一条无依据规则，而不是模糊地判为“差不多”。
第一版不做语义相似、单位换算或模型评分，避免隐藏真实差异。

### 字段如何比较

顶层比较 `airline_code` 和 `airline_name`。每条期望规则比较 9 项：

```text
cabin_class
fare_codes
checked_baggage
pieces
size_limit.length / width / height / note
special_notes
```

除舱位代码无序比较外，其余字段严格比较。`null`、`0`、`""` 与 `[]` 不可互换。
期望为空而实际填值会增加 `unsupported_values`；无依据规则中每个非空事实也计入该指标。

### 分母如何保留

- `case_count` 始终等于数据集案例数。
- 缺少预测会成为 `MissingPrediction`，而不是从报告删除。
- Provider、解析或领域失败保留为失败预测；该案例的期望字段仍进入字段总分母。
- 多余的未知案例 ID 和重复预测 ID 会让评估数据失败，不能静默忽略。
- `exact_match_rate = exact_matches / case_count`。
- `field_accuracy = field_correct / field_total`。
- `prediction_success_rate` 保留调用与输出失败，`rule_recall = matched_rules / expected_rules`。
- `field_metrics` 按顶层字段及两类规则字段分别报告正确数、分母与准确率。

字段准确率不惩罚无依据规则的额外字段，因此必须同时查看
`unsupported_rules` 和 `unsupported_values`，不能只选一个好看的指标。

## 先运行离线评分示例

在 `projects/baggage-extractor` 项目目录执行：

Windows / PowerShell：

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.evaluation.cli score `
  --dataset evals\datasets\v1\dev.jsonl `
  --predictions evals\examples\dev-predictions-with-errors.jsonl `
  --model scorer-demo `
  --prompt-version not-a-model-run
```

macOS / Linux：

```bash
.venv/bin/python -m baggage_extractor.evaluation.cli score \
  --dataset evals/datasets/v1/dev.jsonl \
  --predictions evals/examples/dev-predictions-with-errors.jsonl \
  --model scorer-demo \
  --prompt-version not-a-model-run
```

示例故意包含错误，当前应报告：

```text
case_count: 6
successful_predictions: 5
failed_predictions: 1
exact_matches: 3
exact_match_rate: 0.5
missing_rules: 3
unsupported_rules: 1
unsupported_values: 4
```

`generated_at` 每次不同。该结果是评分器演示，不是模型质量基线。
添加 `--output <path>` 可保存报告；已有文件默认拒绝覆盖，只有明确使用 `--overwrite` 才替换。
即使启用覆盖，CLI 也不会把数据集或预测输入当作报告路径覆盖。

## 动手任务

### 1. 追踪一个错误案例

对照开发数据和示例预测，解释：

1. `zh-dev-carry-size-002` 为什么不是完全匹配。
2. `zh-dev-unrelated-004` 的航司代码和额外托运规则分别如何计数。
3. `zh-dev-multiple-cabins-005` 的失败为什么仍影响字段与规则分母。
4. 舱位代码 `["B", "Y"]` 为什么能匹配期望的 `["Y", "B"]`。

### 2. 完成评分器变式测试

在自己的工作副本中增加测试：

- 从一个满分预测中删除 `size_limit.note`，证明预测文件在评分前就因领域 Schema 失败。
- 提供重复 `case_id`，证明加载器拒绝数据，而不是保留最后一条。
- 把期望的 `pieces: null` 改成实际 `pieces: 1`，断言错误值和 `unsupported_values` 都增加。
- 删除一条预测，证明报告加入 `MissingPrediction` 且 `case_count` 不变。

测试只使用人工数据，不调用模型。记录为什么“评分器测试全绿”仍不等于模型质量通过。

### 3. 扩展开发集

新增一条合成开发案例：

1. 先写输入、期望行为和覆盖标签。
2. 逐字段核对原文；不凭航司常识补全。
3. 保持稳定 ID，确保没有与 v1 原留出集近重复，以保留练习覆盖的差异。
4. 运行数据加载测试。
5. 不修改现有案例答案来让候选 Prompt 获得更高分，也不将本次调试案例移入未来的独立留出集。

优先增加当前覆盖缺口，而不是只增加容易的单规则案例。

## 可选：显式运行真实模型

先阅读[真实调用配置与费用边界](../../../docs/setup.md#真实模型固定评估)。
`run` 会顺序执行所选文件的所有案例，每个案例沿用 Provider 的有限重试。
必须确认最坏 HTTP 请求数：

```text
最大请求数 = 案例数 × (MODEL_MAX_RETRIES + 1)
```

以下示例使用 v1 原留出集做回归，不是独立质量验证。6 条案例、默认 2 次重试时，确认值为 18：

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.evaluation.cli run `
  --dataset evals\datasets\v1\holdout.jsonl `
  --predictions-output evals\runs\candidate-predictions.jsonl `
  --report-output evals\runs\candidate-report.json `
  --confirm-max-requests 18
```

配置或案例数改变后必须重新计算，参数不一致时在创建 Provider 前退出。
本地真实结果默认写入被 Git 忽略的 `evals/runs/`。提交基线前人工检查：

- 不含私人输入或敏感错误文本；
- 数据、Prompt、领域 Schema、模型、包版本与最大重试配置完整；
- 数据实际用途已标明；使用 v1 原留出集时注明“现用于回归”，不宣称是独立验证；
- 调用失败保留在分母；
- 报告没有被手工挑选或只保留最好一次；
- 已写明供应商、日期、运行配置、Token/费用是否采集及限制。

当前运行器记录每案例延迟，报告同时汇总有记录案例的平均延迟；延迟包含内部重试。
Provider 尚未暴露 Token、费用、请求 ID 和实际重试次数；这些字段不能填 0 或声称已验证。
运行时 stderr 显示数据用途与限制、案例 ID、进度与错误类型，不打印政策原文；stdout 保持为 JSON 报告。
当前在全部案例结束后才原子写入预测与报告；进程中断会丢失本轮内存结果，需要重新运行，
这是后续断点恢复能力的明确限制。

## 比较候选版本

先保存当前候选的预测和报告，再只改变一个主要变量，例如 Prompt 或模型。
对同一版本数据重复执行并比较；使用 v1 原留出集只能得到回归结果。
独立质量验证需先准备并冻结未用于调优的新留出集，当前仓库尚未提供。比较内容包括：

- 完全匹配和字段准确率；
- 遗漏规则、无依据规则与无依据值；
- 调用失败及错误类型；
- 延迟分布；当前报告保留逐案例延迟，尚未计算 P95；
- 实际可获得的 Token 与费用；当前未采集。

在看到候选结果前登记门槛。样本只有 6 条时，一个案例就会改变约 16.7 个百分点，
只能作为小型基线，不能做精细统计或就业/生产承诺。

## 常见失败

- **预测文件加载失败**：先看文件路径和报错行号，不跳过坏行继续。
- **规则顺序变化却失败**：检查身份字段或重复舱位代码，而不是强制模型固定数组顺序。
- **字段准确率较高但有臆造**：同时检查无依据规则和值，不能只展示字段准确率。
- **真实运行没有开始**：确认值必须使用当前案例数和重试配置重新计算。
- **已有报告拒绝覆盖**：为新候选使用新文件名；确需替换时显式 `--overwrite`。

## 验收与下一步

- [ ] 能解释数据版本、开发/留出划分和防泄漏规则。
- [ ] 能解释报告的实际用途与限制，知道重命名文件或获得满分都不会使回归集成为独立验证集。
- [ ] 能独立运行离线示例并追踪至少三个错误的计数方式。
- [ ] 完成四个评分器变式测试，程序测试保持离线。
- [ ] 能解释匹配键、严格字段比较和各指标分母。
- [ ] 若执行真实评估，保存完整失败和版本信息；否则标记“模型质量未验证”。
- [ ] 能说明当前数据规模、规则身份和未采集运行指标的限制。

完成本课后，进入[第 7 课：FastAPI 服务化](./07-fastapi-service.md)。
固定评估闭环可用于后续 API、Prompt 和模型变更的回归；独立质量验收还需新留出集与预先登记的门槛。
