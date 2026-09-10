# 固定评估数据

[第 6 课](../lessons/06-fixed-evaluation.md)使用这里的版本化合成数据。

## 数据版本

- `baggage-eval-v1`
- Schema 版本：`1.0`
- `datasets/v1/dev.jsonl`：6 条开发案例，可用于调试评分器和 Prompt。
- `datasets/v1/holdout.jsonl`：6 条固定留出案例，仅用于版本比较和门槛判断，不针对单条答案调 Prompt。

两份数据均为本仓库课程自编的合成文本，不代表真实航司政策，不能用于旅客权益判断。
第一版用于建立端到端评估闭环，不声称覆盖全部航司规则或具有统计代表性。

## 每条记录

| 字段 | 含义 |
| --- | --- |
| `schema_version` | 案例文件契约版本 |
| `dataset_version` | 整体数据版本，同一文件必须一致 |
| `id` | 稳定且唯一的案例 ID |
| `split` | `dev` 或 `holdout`，同一文件不能混用 |
| `policy_text` | 发送给提取器的合成原文 |
| `expected` | 通过领域 Schema 校验的人工期望结果 |
| `tags` | 覆盖标签；同一案例内不可重复 |
| `source` | 当前只接受 `synthetic`，避免来源含糊 |

期望数据中，同一数组不能出现相同的“舱位说明 + 无序舱位代码”身份，
同一规则不能包含重复舱位代码，否则评分器无法确定配对，加载时会拒绝。
加载器也拒绝 JSON 重复键、重复案例 ID、混合版本和混合 split，不保留最后一条来掩盖数据问题。

## 离线检查

仓库提供一份故意含错的开发集预测，用于观察评分行为：

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.evaluation.cli score `
  --dataset evals\datasets\v1\dev.jsonl `
  --predictions evals\examples\dev-predictions-with-errors.jsonl `
  --model scorer-demo `
  --prompt-version not-a-model-run
```

命令不读取模型配置、不发网络请求。报告包含整体与逐字段准确率、规则召回、
遗漏/无依据规则、无依据值、失败预测、逐案例问题和可用延迟。
完整解释、macOS/Linux 命令和真实评估边界见[第 6 课](../lessons/06-fixed-evaluation.md)。

## 修改规则

- 修正明确的标注错误时，记录原因并升级数据版本；不要为提高某次模型得分临时改答案。
- 新案例先进入开发集，人工复核后再形成下一版留出集。
- 同源或近重复案例不跨开发集与留出集，避免泄漏。
- 扩展英文、单位换算、会员或冲突处理时，先更新领域范围和评分规则，再单独扩展数据。
- 不提交旅客、客户、公司内部资料或无法确认再分发条件的网页正文。

仓库不保存伪造的“模型基线”。只有显式运行真实模型后，才能把带模型、Prompt、代码和数据版本的报告
保存为模型质量基线；离线满分预测只能用于校准评分器。
