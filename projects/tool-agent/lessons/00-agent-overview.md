# 00 · 先跑一个有边界的 Agent（60–90 分钟）

[课程入口](../../../README.md) · [项目说明](../README.md) · [环境准备](../../../docs/setup.md)

**适合谁**：会 Python、异常、pytest 的工程师；不用从语法开始。
**完成后**：能沿 trace 解释「模型提议工具 → 程序验证并执行 → observation → 再次调用」，
并说清哪些行为是代码保证、哪些还没有被证明。

## 1. 跑通工作演示（15–20 分钟）

按[项目安装步骤](../README.md#安装与运行)准备 Python 3.13+，进入 `projects/tool-agent`。
以下 `python` 使用项目虚拟环境解释器（Windows 可用 `.\.venv\Scripts\python.exe`，
macOS 可用 `.venv/bin/python`）。

```text
python -m tool_agent --scenario success
python -m pytest -q
```

找出 `mode`、`termination`、`steps`、`tool_calls`。预期 success 为 3 步、2 次真实工具执行。
注意：工具是真的运行了，但模型请求和最后答案是**硬编码离线脚本**，不是模型推理。

## 2. 沿一次请求读代码（20–25 分钟）

依次打开 `src/tool_agent/demo.py`、`contracts.py`、`agent.py`、`tools.py`：

1. 找 `ScriptedProvider.complete` 中三个固定回合，标出答案在哪一行预先写好。
2. 找 `Agent.run` 如何保存 assistant 请求和带 `tool_call_id` 的工具 observation。
3. 找 `ToolRegistry.prepare`，解释为什么仅在 prompt 写“不要读私有文件”不够。
4. 找 `untrusted-note` 中恶意指令。它是教材数据，不是需要执行的操作。

区分普通函数管道与 Agent 循环：真实 Agent 由模型决定下一步；这里用固定脚本替代模型，
只便于观察相同接口和控制流，不能凭 success 宣称模型会规划或抵抗注入。

## 3. 做失败路径巡检（15–25 分钟）

逐条执行；非成功的非零退出是正确行为：

```text
python -m tool_agent --scenario denied
python -m tool_agent --scenario tool-error
python -m tool_agent --scenario step-limit --max-steps 2
python -m tool_agent --scenario timeout --timeout 0.05
```

PowerShell 用 `$LASTEXITCODE`，macOS 用 `$?`。比较 denied 的 **0 次派发**
和 tool-error 的 **1 次失败执行**；说出为什么不能都返回“查询成功但无结果”。

## 任务起点（10–20 分钟）

不扩展框架，不接 API：把 success 的工具预算改为 1，预测终止原因再执行验证。
然后打开 `exercises/authorization.py`，定位明确未实现的授权函数；下一课完成它。
可运行 `python -m pytest exercises/test_authorization.py -q --tb=short` 观察预期 6 个失败，
但不要把这条故意红灯命令混入默认验收命令。

## 验收（4 项）

- [ ] 默认测试通过，success 为 3 步 / 2 工具，能指出两次实际派发的 trace。
- [ ] 能复现 denied / tool-error / step-limit / timeout，退出码分别为 3 / 4 / 6 / 8。
- [ ] 能展示授权在 Python 中强制执行，而不是依赖模型遵守提示。
- [ ] 能解释“固定脚本演示成功 ≠ 真实模型质量或提示注入防御已验证”。

下一步：[05 · 工具契约](05-tool-contracts.md)。参考实现就是当前可运行项目，不另建应用。
