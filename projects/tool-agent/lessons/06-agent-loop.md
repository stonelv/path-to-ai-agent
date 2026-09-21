# 06 · 手写最小 Agent Loop

[课程入口](../../../README.md) · [项目说明](../README.md) · [环境准备](../../../docs/setup.md)

**目标**：亲自实现模型 → 工具 → observation 的有界循环，而不是只看演示或写无限循环。
先完成 [05 工具契约](05-tool-contracts.md)。约 60–90 分钟。
在 `projects/tool-agent` 下使用项目虚拟环境 Python。

## 先观察一次反馈（10 分钟）

```text
python -m tool_agent --scenario success
python -m pytest exercises/test_agent_loop.py --reference -q
```

演示实际运行工具，但模型和答案是固定脚本。参考验收应 **13 个通过**，
使用的是生产 `Agent.run`，不是学生 starter，也不证明真实模型质量。
读 `contracts.py` 的 `Message` / `ModelTurn`，指出工具调用 ID 如何关联 observation。

## 实现任务：补全小循环（30–45 分钟）

起点是 `exercises/agent_loop.py` 的 `run_loop`，目前明确抛出 `NotImplementedError`：

```text
python -m pytest exercises/test_agent_loop.py -q --tb=no
```

初始预期 **13 个失败**；调试时换 `--tb=short`。这组测试不进入默认 suite。
复用现有 `Provider`、`ToolRegistry`、`validate_turn`、`Limits`、`Result` 与消息类型，
不复制工具、provider 或整个应用。**不得调用 `Agent.run`**，练习模式会禁用它。

按以下顺序实现：

1. 建立 system / user 消息，调用 `provider.complete` 并用 `validate_turn` 验证返回。
   每次请求计一步；最后一个允许步骤收到最终答案仍然 success。
2. 工具回合先检查剩余调用预算，并对**整轮**调用执行 `registry.prepare`；
   任一请求无权限或参数非法，整个回合零派发，不能先执行第一个合法工具。
3. 保存 assistant 工具请求；顺序 `await registry.execute`，开始执行就计一次调用，
   失败也占用预算。把 observation 转成 JSON，通过带 `tool_call_id` 的 tool 消息反馈。
4. 用 `Result` 返回 answer、steps、tool_calls、termination。明确处理 denied、
   invalid_request、tool_error、provider_error、step_limit、tool_limit，不能伪造答案。
   仅将预期 `ProviderFailure` / `ToolFailure` 转成脱敏失败结果；
   不要捕获所有异常来隐藏意外编程错误。
5. 用 `asyncio.timeout` 包围整个循环，包含模型与工具等待，不能每轮重置。
   捕获 `TimeoutError` 后先检查 `deadline.expired()`：只有本范围到期才返回 timeout，
   内部无关的 `TimeoutError` 必须继续传播。到期取消当前等待，但合作式异步超时
   不能强杀阻塞函数或吞掉取消的代码。

参考实现是 `src/tool_agent/agent.py`；建议先独立写，再对照。
验收关注真实派发、反馈与边界，不要求精确 trace 顺序。可记录简短公开事件，
不记录私有思维链。测试自身有外层保护超时，但不能拿它代替练习中的截止时间。

## 独立迁移：合成发布核对（10–20 分钟）

不扩展平台、不添加新工具：自行构造两份合成文档（发布清单和测试摘要）、独立授权集合
及一个实现 `Provider` 协议的离线脚本。第一轮请求两份文档；下一轮必须使用收到的
observation 生成核对结果，不能预写固定答案。复用自己实现的 `run_loop`。

自行加一个测试：只授权其中一份文档，断言整轮零派发；再授权两份，断言结果来自实际
工具正文且两次派发有序。不要把答案字符串测试当作派发证据。不接真实发布系统或网络。

## 复核与验收（10–15 分钟）

```text
python -m pytest exercises/test_agent_loop.py -q
python -m pytest exercises --reference -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

第一条证明自己实现通过 13 项契约；第二条证明两个参考实现共 19 项契约通过。
预算和超时也可观察 CLI：
`python -m tool_agent --scenario success --max-tool-calls 1` 应退出 7；
`python -m tool_agent --scenario timeout --timeout 0.05` 应退出 8。

- [ ] 未完成 stub 已被真实循环替换，不调用 `Agent.run`；13 项学生验收通过。
- [ ] 实际工具参数、assistant 请求和不可信 observation 完成反馈；无权限整轮零派发。
- [ ] 步数、工具预算、工具错误、最终步成功、模型/工具累计超时均明确终止。
- [ ] `ProviderFailure` 转为 provider_error，意外编程异常仍可见；默认测试与 Ruff 通过。
- [ ] 完成独立发布核对迁移，以真实工具正文和派发证据证明反馈，不只改演示文案。
