# 05 · 把工具契约和权限写进程序

[课程入口](../../../README.md) · [项目说明](../README.md) · [环境准备](../../../docs/setup.md)

上一课：[04 · 可靠性](../../baggage-extractor/lessons/04-reliability.md)。

**目标**：完成一个真实未实现的授权函数，区分参数错误、拒绝访问与执行失败。
先完成 [00 总览](00-agent-overview.md)。约 45–60 分钟；已有 Python 经验，不复习语法。
命令均在 `projects/tool-agent` 下，用已安装项目的虚拟环境 Python。

## 观察（10 分钟）

```text
python -m tool_agent --scenario denied
python -m tool_agent --scenario tool-error
python -m pytest tests/test_tools.py -q
```

读 `src/tool_agent/tools.py`：

- `ToolDefinition.parameters` 给 provider 描述工具，但不会自动替你执行参数验证。
- `validate_read_arguments` 要求且仅要求 `doc_id` 字符串，不接受 `True`、额外字段或路径。
- `prepare` 先查工具 allowlist，再验证参数、校验资源集合；不授权就不派发。
- 已授权但缺失的资源是 `ToolFailure`，不是默认成功。
- 输出截断且标记 `untrusted`；恶意正文仍然是数据。输出上限不等于权限检查。

## 实现任务（20–30 分钟）

本课 starter：`exercises/authorization.py` 中的 `authorize_read`，现在会
`raise NotImplementedError`。不要复制整套工具或 Agent。

1. 先跑故意红灯测试，预期 6 个失败：
   `python -m pytest exercises/test_authorization.py -q --tb=no`。
2. 复用 `validate_read_arguments` 获取标识；让非法参数继续抛 `InvalidArguments`。
3. 检查 `allowed_docs`；合法但未授权的标识抛 `ToolDenied`。
4. 只返回已授权标识，不能读取文件、调用工具或返回正文。
5. 再跑同一测试，应为 6 个通过。参考答案：`ToolRegistry.prepare` 的读取分支；
   尝试独立完成后再对照。

这组测试被 `pyproject.toml` 的 `testpaths = ["tests"]` 排除在默认 suite 之外；
显式运行练习路径才会收集它。未完成 starter 不影响工作演示。
调试时可把 `--tb=no` 换成 `--tb=short`。下一课另有小型循环 starter，并非第二套应用。

## 验证（10–20 分钟）

```text
python -m pytest exercises/test_authorization.py --reference -q
python -m pytest tests/test_agent.py -k "denial or authorized or injection" -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

`--reference` 将同样的 6 项验收直接运行在生产 `ToolRegistry.prepare` 上，应全部通过；
它不会填写 starter，也不能替代不带该选项的学生实现验收。

观察 `test_injected_text_does_not_grant_resource_authorization`：即使模拟模型请求了恶意正文
要求的私有文档，程序仍会拒绝。它**没有**证明任何真实模型会忽略恶意指令。

## 验收（4 项）

- [ ] starter 不再抛 `NotImplementedError`，显式练习测试 6 个通过。
- [ ] 多余字段、错误类型、相对/绝对路径不能绕过严格参数验证。
- [ ] 禁止访问在执行前返回 denied，调用计数为 0；授权但缺失返回 tool_error。
- [ ] 默认测试与 Ruff 通过，能解释正文长度上限、`untrusted` 与资源授权的不同职责。

下一步：[06 · Agent 循环](06-agent-loop.md)。
