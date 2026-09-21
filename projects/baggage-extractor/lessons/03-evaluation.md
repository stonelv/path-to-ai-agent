# 第 03 课：用评估改进结果

上一课：[结构化输出](./02-structured-output.md) · [返回课表](../../../README.md) · 下一课：[可靠调用](./04-reliability.md)

前置：第 02 课、JSONL。建议 2～3 小时。先使用评分器，不要求实现配对算法。

## 问题与必要概念

Prompt 修改后答案更自然，不代表提取更准确。
先固定输入和期望结果，再比较遗漏、无依据补充、完整匹配与调用失败。

| 验证 | 可以证明什么 |
| --- | --- |
| 程序测试 | 评分公式与失败处理符合约定 |
| 保存的人工预测评分 | 评分器能识别设计好的错误 |
| 真实模型评估 | 特定模型、Prompt、数据与运行条件下的效果 |

失败必须留在分母里。当前数据只有 6 条开发和 6 条原留出案例，不具统计代表性；
原留出集已参与 Prompt v2 调优，现在只能用于回归，详见[数据说明](../evals/README.md)。

## 动手任务

1. 运行含错示例，找出遗漏、无依据补充和调用失败的案例，不只看总分。
2. 将示例预测复制到自己的 `evals/runs/`，只纠正一个已识别的错误，再用相同数据评分。
   保持案例 ID 和数据不变，分别记录改前、改后的指标；这是评分器练习，**不是 Prompt 改进证据**。
3. 在自己的评分器测试中补充：缺少一条预测时，报告包含 `MissingPrediction` 且总案例数不变。
4. 写出一个 Prompt 改进假设及真实验证方案：固定模型、输入、参数和数据，只改 Prompt，
   保留全部预测与失败，不提前填写预期得分。

## 运行与预期

在项目目录执行：

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.evaluation.cli score --dataset evals\datasets\v1\dev.jsonl --predictions evals\examples\dev-predictions-with-errors.jsonl --model scorer-demo --prompt-version not-a-model-run
.\.venv\Scripts\python.exe -m pytest tests\test_evaluation_scorer.py tests\test_evaluation_loader.py tests\test_evaluation_cli.py
```

macOS/Linux 使用 `.venv/bin/python`，文件路径改为 `/`。预期示例：

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

输出是 JSON 报告，以上为需核对的字段。第二轮将 `--predictions` 改成自己的文件，
`--model` 仍使用 `scorer-demo`，不要伪装真实模型。
用 `--output` 保存报告时默认拒绝覆盖；只有确需替换时显式加 `--overwrite`。

## 一个失败案例

删除失败预测再评分不会“去掉坏样本”：缺失预测仍计为失败，总分母不变。
字段准确率也不能单独使用，因为它不惩罚所有无依据的额外字段；同时检查无依据规则与值。

## 验收

- 能复现示例指标，并根据逐案例问题解释总分。
- 完成一次受控的人工预测修改，说明改动影响哪些指标。
- 用测试证明失败不会从分母中消失。
- 能区分“评分器练习”“同集回归”和“独立质量验证”。

## 可选深入

有账户并确认预算后，按[真实评估命令](../README.md#固定真实评估)运行基线，
再比较一个 Prompt 版本。记录模型、代码、Prompt、Schema、数据版本、完整预测与报告。
在比较前确定适用的质量门槛，不事后改阈值宣称通过；未运行写“真实模型未验证”。
配对算法、逐字段分母与更多案例放到[评分器](../src/baggage_extractor/evaluation/scorer.py)中按需研究。
