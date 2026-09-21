# 第 01 课：模型调用与行为边界

[返回课表](../../../README.md) · 下一课：[结构化输出](./02-structured-output.md)

前置：完成[环境准备](../../../docs/setup.md)，会 HTTP、JSON 和基本 `async/await`。
建议 1～2 小时。本课离线可完成，不验证真实模型效果。

## 问题与必要概念

输入“经济舱可免费托运1件23kg行李”，模型可能输出正确文本，也可能漏掉件数、猜测航司，
或因输出预算用尽而截断。接口返回 200 不代表内容正确。

- 模型根据上下文生成输出，不是事实数据库；系统指令、用户输入和提供的资料都会影响结果。
- messages 是本次请求携带的信息；上下文窗口与输出 Token 上限不是字符数或费用保证。
- Temperature 影响采样，不是准确率开关；设为 0 也不能证明结果永远相同。
- 普通规则足够解决的任务优先用规则；固定步骤用工作流，需要动态选择工具时才考虑 Agent。

## 动手任务

1. 阅读[请求契约](../src/baggage_extractor/providers/base.py)，画出
   `ModelRequest → ModelProvider.generate → ModelResponse`。暂不研究 HTTP 适配器内部。
2. 在自己的 `tests/test_my_model_call.py` 中写一个异步 Stub：
   保存收到的请求，返回 `ModelResponse(content="1件23kg", model="scripted")`。
   构造一条用户消息，调用它，断言角色、原始输入、正文和模型名称。
3. 用同一个输入分别让 Stub 返回“23kg”和“某航空1件23kg”，列出遗漏与无依据补充。
   这是人工构造的错误练习，不是模型实验。
4. 阅读[HTTP 协议测试](../tests/test_openai_compatible_provider.py)，为缺少 `x-request-id`
   的成功响应补一条测试：正文保留，`request_id is None`，不虚构供应商请求 ID。

## 运行与预期

在项目目录执行；macOS/Linux 替换解释器为 `.venv/bin/python`，文件路径使用 `/`：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_provider_base.py tests\test_openai_compatible_provider.py tests\test_my_model_call.py
```

先完成第 2 项创建测试文件，再运行命令。预期退出码 0，无网络和费用。
运行已有测试只能证明环境与参考实现可用，自己写的 Stub 测试才是本课交付之一。

## 一个失败案例

HTTP 200 但 `content` 为空时，适配器会抛出 `InvalidResponseError`，而不是返回空字符串冒充成功。
找到对应测试，解释“HTTP 成功”“协议有效”“事实正确”为什么是三件事。

## 验收

- 能从空白测试文件完成一次 Stub 请求，并解释三个契约对象的职责。
- 能识别遗漏、无依据补充与截断，说明本地契约无法证明事实正确。
- 完成可选请求 ID 的测试，区分 Stub、HTTP Mock 与真实模型验证。
- 能举例说明无需使用 LLM 或 Agent 的任务。

## 可选深入

按[项目运行说明](../README.md#可选真实模型)显式运行真实调用，逐字段对照原文。
比较参数时固定输入、模型、Prompt 和其他配置，只改变一个变量；重复少量试验只作探索性结论。
记录全部输出、失败和版本；没有账户直接跳过，不把 Stub 数据标成真实结果。
