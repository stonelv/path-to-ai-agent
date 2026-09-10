# 第 2 课：模型调用、契约与实验

上一课：[工程初始化](./01-project-setup.md) · [课程索引](./README.md) · 下一课：[错误处理](./03-error-handling.md)

## 目标与前置

建议 2～3 小时。需要完成第 1 课，理解 HTTP 与 JSON，并能阅读简单的 async/await。
本课不追求“返回看起来不错的答案”，而是理解供应商边界、调用元信息，以及离线测试能证明什么。

## 最小概念

- `ModelRequest` / `ModelResponse` 是业务契约，不把供应商的 HTTP 响应对象传给业务。
- `ModelProvider` 用 Protocol 描述所需能力；Stub 可不继承某个基类而满足契约。
- HTTP 200 不等于模型给出了可用回答；当前适配器拒绝缺少 choices 或空正文。
- 当前回答仍是文本，尚未经过行李额领域 Schema 校验。

## 动手任务

1. 先画出[实验案例](../src/baggage_extractor/experiments.py)到[请求契约](../src/baggage_extractor/providers/base.py)、
   [适配器](../src/baggage_extractor/providers/openai_compatible.py)、[计时包装](../src/baggage_extractor/telemetry.py)和[入口](../src/baggage_extractor/main.py)的调用关系。
2. 阅读[成功请求测试](../tests/test_openai_compatible_provider.py)，预测 URL、messages、temperature、max_tokens 和返回模型名称。
3. 运行下方参考测试。区分 Stub 验证接口契约、HTTP Mock 验证请求/响应、真实模型实验验证实际行为的不同用途。
4. 在自己的工作副本中新增一个 HTTP Mock 测试：
   返回含合法正文与模型名称的响应，但不提供 `x-request-id`；断言正文和模型保留，`request_id is None`。
   同时构造默认 `max_output_tokens=None` 的请求，断言发送的 JSON 不包含 `max_tokens`。
5. 用[学习记录模板](../../templates/learning-log.md)记录调用路径和测试结果。

## 运行与预期

在项目目录执行：

Windows / PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_provider_base.py tests\test_openai_compatible_provider.py tests\test_telemetry.py tests\test_experiments.py
```

macOS / Linux：

```bash
.venv/bin/python -m pytest tests/test_provider_base.py tests/test_openai_compatible_provider.py tests/test_telemetry.py tests/test_experiments.py
```

参考测试和新增测试应通过，不发送真实请求。计时测试断言非负延迟和起止顺序，不断言固定耗时。
现有适配器测试还包含下一课的错误路径，可以先不深入退避实现。

<details>
<summary>提示与参考实现</summary>

- 复用现有测试中的 settings fixture 和 `@respx.mock`，不要使用真实服务 URL 或密钥。
- 适配器只有在输出上限非空时才添加 `max_tokens`。
- 请求 ID 从响应头中读取；缺失时是 `None`，不应虚构一个供应商 ID。
- 计时采用单调时钟计算耗时、UTC 时间记录事件，二者用途不同。

</details>

## 可选：真实模型观察与受控实验

先阅读[真实调用配置、协议和费用边界](../../docs/setup.md#可选真实模型调用)，再执行其中的命令。
当前入口会运行三组案例，输出文本回答及元信息；没有 API Key 时跳过，并记录“真实模型未验证”。

[作者历史实验](../docs/day-02-model-experiments.md)同时改变了文本、Temperature 和输出上限，只能用于观察，不能说明哪个参数导致变化。
进一步实验时，在自己的分支调整案例，并遵循以下设计：

1. 固定同一段合成政策、模型、Prompt 和输出上限，仅改变 Temperature。
2. 每个设置重复相同次数，例如 3 次；先计算请求数量并确认预算。样本很少时只作探索性结论。
3. 预先列出应提取的信息，分别记录缺失、无依据补充和响应失败。
4. 用[实验报告模板](../../templates/experiment-report.md)保存设置、所有结果及波动，不只保留最好的一次。

当前没有通用实验 runner 或自动评分器，需要自行调整案例并记录结果；不把这项扩展描述成现成 CLI 功能。

## 常见问题与验收

- HTTP 200 但空正文：当前会明确失败；部分模型的推理过程可能消耗输出预算，不能将其当成已完成回答。
- 参数被拒绝：先核对模型是否支持 temperature / max_tokens，“兼容接口”不保证能力完全一致。
- 模型名称或回答与历史记录不同：不是单独的失败标准，应按实际配置与期望行为判断。

- [ ] 契约、适配器、计时和实验构造测试通过，完成可选字段变式测试。
- [ ] 能解释 Mock 测试通过为何不等于模型提取正确。
- [ ] 能区分响应 Schema 校验与业务领域 Schema 校验。
- [ ] 能指出三组历史实验无法做参数因果归因的原因。
