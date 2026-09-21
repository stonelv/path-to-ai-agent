# Tool Agent：有边界的只读工具循环

面向已有 Python 经验的工程师；Python **3.13+**，`src` 布局，运行时仅用标准库。
**默认且唯一模式是 OFFLINE scripted mechanism demo：没有真实模型、API、密钥或网络调用。**
脚本预先决定工具请求和最终答案，展示工程机制，不评测模型质量、推理或自主规划能力。

从[课程入口](../../README.md)进入，环境问题见[环境准备](../../docs/setup.md)。
建议先完成 [00 总览](lessons/00-agent-overview.md)，再读
[05 工具契约](lessons/05-tool-contracts.md)和 [06 Agent 循环](lessons/06-agent-loop.md)。
仅覆盖这三个单元；不实现 RAG、记忆、MCP、多 Agent 或生产部署。

## 安装与运行

以下从仓库根目录开始。首次安装开发工具可能联网；安装后演示与测试不需要联网。
不需要 `.env`。建议使用项目虚拟环境，避免污染其他项目。

Windows PowerShell（不必激活虚拟环境）：

```powershell
cd projects\tool-agent
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m tool_agent
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

macOS / Linux：

```bash
cd projects/tool-agent
python3.13 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m tool_agent
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

以下课程命令中的 `python` 均指上面虚拟环境中的解释器；可替换成其完整路径，
或先激活环境。安装后也提供 `tool-agent` 入口。

```text
python -m tool_agent --scenario success
python -m tool_agent --scenario denied
python -m tool_agent --scenario tool-error
python -m tool_agent --scenario step-limit --max-steps 2
python -m tool_agent --scenario timeout --timeout 0.05
```

每条命令都输出 JSON；**后四条非零退出是预期行为**，不要用只继续成功命令的
`&&` 串联它们。PowerShell 用 `$LASTEXITCODE`，macOS / Linux 用 `$?` 查看退出码。
`--max-steps` 默认 6，`--max-tool-calls` 默认 10，均为 1–100 的整数；
`--timeout` 默认 1 秒，必须为有限正数且不超过 60 秒。

## 架构与边界

```text
用户请求 → Agent.run → Provider.complete(messages, tool definitions)
                         ↓ ModelTurn(answer OR tool_calls)
          契约检查 → 整轮预算/授权预检 → 顺序执行 allowlist 工具
                         ↓ 不可信且有长度上限的 observation
                      下一轮模型请求 / 明确终止
```

- `src/tool_agent/contracts.py`：类型化 provider 协议、公开消息、工具请求与工具定义。
  没有私有思维链字段。协议不依赖任何模型厂商。
- `tools.py`：仅 `list_docs({})` 与 `read_doc({"doc_id": "..."})`。
  schema 提供说明，实际 Python 校验才是边界：拒绝缺失、多余、错误类型和路径参数，
  不把布尔值/数字强制转成字符串。每次执行前校验 allowlist 与文档授权集合。
- 工具仅访问内存中的**合成文档**；没有通用读文件、shell、HTTP、写操作或动态注册。
  `doc_id` 是最多 48 字符的小写目录标识，不是路径；绝不打开任意文件。
  列表也只返回已授权且存在的文档。
- 工具正文默认最多 **400 个 Unicode 字符**（配置范围 32–4096），超出截断并标记
  `truncated: true`。上限针对正文，不含 JSON 转义与 envelope 开销；不是字节上限。
  所有 observation 标记 `untrusted: true`，包括列表；截断不会变成可信内容。
- `agent.py`：顺序循环；一步是一次模型请求。工具预算统计开始执行的调用（失败也计数），
  不包括被预检拒绝的调用。整轮请求必须全部满足契约、权限和剩余预算才会执行第一个工具。
  `ToolFailure` / `ProviderFailure` 等预期契约失败明确终止，并使用脱敏错误说明；
  不悄悄给默认答案。意外编程异常继续传播，不能被包装成正常业务失败。
- `asyncio.timeout` 包围整个循环，包含模型和工具时间，不是每步重新计时。
  仅当该范围的 `deadline.expired()` 为真时将 `TimeoutError` 分类为整体 timeout；
  内部代码自身抛出的无关 `TimeoutError` 仍然传播。
  超时取消正在等待的协程；**仅适用于合作式异步代码**，无法强杀阻塞函数、
  CPU 死循环或吞掉取消信号的第三方实现。这不是进程隔离沙箱。
- `demo.py`：固定离线脚本；success 真实调用列表和读取工具，读到含恶意指令的合成便笺，
  然后返回预先写好的答案。denied 请求受限文档；tool-error 请求已授权但缺失的文档；
  step-limit 不断读同一公开文档；timeout 模拟异步等待。

## 结果与可观察性

stdout 是稳定排序的 JSON，无时间戳、随机 ID 或耗时；同参数/脚本路径输出可重复。
真实系统的超时边界受调度影响，不应拿时间敏感的运行结果当快照保证。

```json
{
  "mode": "offline_scripted_mechanism_demo_not_model_quality",
  "scenario": "denied",
  "termination": "denied",
  "answer": null,
  "steps": 1,
  "tool_calls": 0,
  "events": [
    {"event": "model_requested", "step": 1},
    {"event": "model_returned", "step": 1, "tool_requests": 1},
    {"event": "tool_rejected", "step": 1, "tool": "read_doc", "call_id": "read-1"},
    {"event": "terminated", "step": 1, "reason": "denied",
     "detail": "Access to this document is forbidden."}
  ]
}
```

success 还包含 `tool_started`（调用 ID、校验后的参数）和 `tool_finished`（受限 observation）。
trace 记录公开动作而非私有推理；预期工具/provider 契约错误不输出异常原文。此数据完全合成；
若将来引入真实数据，应另行设计日志脱敏与保留策略。

| termination | 退出码 | 含义 |
| --- | --- | --- |
| `success` | 0 | 收到最终答案，不等于答案正确 |
| `denied` | 3 | 工具或资源不被允许 |
| `tool_error` | 4 | 已授权工具执行失败 |
| `invalid_request` | 5 | 请求、模型返回结构或工具参数不合法 |
| `step_limit` | 6 | 模型步数耗尽 |
| `tool_limit` | 7 | 下一轮会超出工具预算 |
| `timeout` | 8 | 整体截止时间到达 |
| `provider_error` | 9 | provider 异常，没有降级答案 |

CLI 参数错误沿用 argparse 的退出码 2，错误写入 stderr，不承诺 JSON。
意外编程异常不属于结果协议，会继续抛出；应修复问题而非依赖其退出码或 JSON 形状。
`python -m tool_agent --scenario success --max-tool-calls 1` 可额外观察 `tool_limit`。

## 验证与真正的实现练习

```text
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

默认测试只收集 `tests/`：验证实际工具调用、准确参数、observation 回传、拒绝时不派发、
整轮预检、顺序执行、两种预算、模型/工具整体超时、错误终止、JSON 与进程退出码。
恶意输出测试验证的是**程序授权不能被越过**，不是模型抵抗提示注入的能力。
没有真实模型、质量评估、联网集成或生产安全认证。

两个小型实现 starter 均明确抛出 `NotImplementedError`，不被生产代码引用：

```text
python -m pytest exercises/test_authorization.py -q --tb=no
python -m pytest exercises/test_agent_loop.py -q --tb=no
```

- 05：`exercises/authorization.py`，先校验、再授权、返回标识；初始 **6 个失败**。
- 06：`exercises/agent_loop.py`，手写模型 → 工具 → observation 的最小有界循环；
  初始 **13 个失败**。复用协议、契约验证、registry、Limits / Result，不复制应用，
  **不能调用 `Agent.run`**；练习模式会禁用它。验收不约束 trace 的精确顺序。

默认 `python -m pytest -q` 仅收集 `tests/`，故意红灯练习不进入默认 suite。
`--tb=no` 保留简短失败清单；调试时换 `--tb=short`。完成实现后运行以上命令应分别
得到 6 / 13 个通过，不能修改断言绕过权限或预算。

同一组验收可切换到生产参考实现，**不需要先填写 starter**：

```text
python -m pytest exercises/test_authorization.py --reference -q
python -m pytest exercises/test_agent_loop.py --reference -q
python -m pytest exercises --reference -q
```

预期分别为 **6 / 13 / 19 个通过**。授权参考直接调用 `ToolRegistry.prepare`；
循环参考直接调用 `Agent.run`，不是另一份答案代码。`--reference` 验证契约与参考实现，
不代表你的 starter 已完成。然后跑默认测试与 Ruff。[06](lessons/06-agent-loop.md)
还要求独立构造合成发布核对场景，在不扩展平台的前提下验证迁移。
