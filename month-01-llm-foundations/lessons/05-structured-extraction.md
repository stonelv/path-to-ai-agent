# 第 5 课：首个结构化提取闭环

上一课：[领域 Schema](./04-domain-schema.md) · [课程索引](./README.md)

## 目标与前置

建议 3～5 小时。需要完成第 4 课，理解 Provider 协议、HTTP Mock 和异常传播。
当前已有参考实现；本课通过追踪代码和独立变式学习，不要求重复新建已有文件。
完成后应能用离线测试证明以下闭环及其失败边界：

```text
政策文本 → 带 JSON Schema 的请求 → JSON 正文 → 领域校验 → ExtractionResult
```

本课不实现 FastAPI、RAG、Agent Loop 或模型质量评估器。
课程是否发布见[首页状态](../../README.md#课程状态)，下方验收清单由学习者自己填写。

## 职责边界

| 层 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| Provider | HTTP、认证、结构化请求参数、响应协议、有限重试 | 行李领域模型 |
| Extractor | 输入、Prompt、JSON 解析和领域校验 | 读取密钥、创建 HTTP 客户端 |
| 领域模型 | 必填键、类型、值约束、未知字段 | 判断事实是否来自原文 |
| CLI | 参数、输出、非零失败退出码 | 把失败改成空结果 |

领域语义统一见[Schema 文档](../docs/schema.md)，不在本课复制字段表。
Prompt 不能替代程序校验；Pydantic 校验通过也不能证明模型没有臆造。

## 动手任务

### 1. 追踪一次结构化调用

阅读[请求契约](../src/baggage_extractor/providers/base.py)、
[适配器](../src/baggage_extractor/providers/openai_compatible.py)、
[提取器](../src/baggage_extractor/extractor.py)和[Prompt](../src/baggage_extractor/prompts.py)：

- `ModelRequest.structured_output` 默认是 `None`，普通文本实验不发送 `response_format`。
- `StructuredOutputSpec` 表达名称、描述、JSON Schema 和 strict，不传供应商 SDK 对象。
- 适配器把它映射为 `response_format.type=json_schema`；不支持时明确失败，不静默退化。
- 提取器从 `ExtractionResult.model_json_schema()` 生成 Schema，并关联 Prompt 版本。
- 请求认证从 Settings 的 SecretStr 显式读取；Mock 只使用测试密钥，不打印真实凭据。

先预测请求字段，再对照[HTTP 测试](../tests/test_openai_compatible_provider.py)确认。

### 2. 区分四类失败

阅读[提取异常](../src/baggage_extractor/errors.py)与[提取器测试](../tests/test_extractor.py)：

| 输入或响应 | 预期行为 |
| --- | --- |
| 空白或超过 20,000 字符 | InvalidExtractionInputError，Provider 调用 0 次 |
| Markdown 包裹、损坏 JSON、重复对象键或非标准数值常量 | StructuredOutputParseError，不修复、不再调用模型 |
| JSON 合法但缺键或类型错误 | StructuredOutputValidationError |
| Provider 认证、限流、连接、超时或无效响应 | 保留 Provider 原异常类型 |

重复键即使能被默认 JSON 解析器接受，也会覆盖前值，本项目明确拒绝。
`NaN`、`Infinity` 不是标准 JSON 数值。空正文、明确拒绝、截断等协议问题由 Provider 处理，
不要在 Extractor 中重复实现 HTTP 协议判断。

### 3. 完成自己的变式练习

在自己的工作副本中补充以下测试，不修改现有断言来迁就错误结果：

1. **输入上界**：恰好 20,000 字符时 Provider 调用一次，20,001 字符时零次。
   使用 Stub，不发送大文本到真实服务。
2. **嵌套失败**：在合法 Stub 结果的随身行李规则中，把 `pieces` 改为 `"1"`，
   断言领域校验失败且不额外调用 Provider；解释为何不自动把字符串转成整数。
3. **CLI 的非法正文**：让 Stub 返回非 JSON，断言退出码为 1、stdout 为空，
   stderr 有明确错误，不包含 Stub 原始正文。

先写预期，再运行参考实现；在[学习记录](../../templates/learning-log.md)中解释
为什么“合法空规则”与“提取失败”不能混为一谈。
可选择其中一个小测试做[AI 编程协作练习](../../docs/coding-agent-workflow.md)，但自己审查 diff 和结果。

### 4. 核对两个入口

[实验入口](../src/baggage_extractor/main.py)继续运行三组文本实验，不改成结构化 CLI。
[提取 CLI](../src/baggage_extractor/extract_cli.py)从位置参数读取一段文本，
成功只输出格式化 JSON；输入、配置、提取和 Provider 错误使用非零退出状态。
配置错误只展示字段名，不输出可能含凭据的校验输入。

CLI 测试注入 Provider，不能依赖真实 `.env`、外部模型或当前账户额度。

## 离线运行与预期

在第一月项目目录使用已有虚拟环境，安装方式见[环境指南](../../docs/setup.md)。

Windows / PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_extractor.py tests\test_extract_cli.py tests\test_openai_compatible_provider.py tests\test_provider_base.py tests\test_prompts.py
.\.venv\Scripts\python.exe -m ruff check .
```

macOS / Linux：

```bash
.venv/bin/python -m pytest tests/test_extractor.py tests/test_extract_cli.py tests/test_openai_compatible_provider.py tests/test_provider_base.py tests/test_prompts.py
.venv/bin/python -m ruff check .
```

测试与新增变式应通过，不需要 API Key，不产生真实模型请求。
Stub 只能证明给定响应时程序的行为，不能证明模型会返回正确规则。

## 可选真实模型冒烟

统一按[结构化提取运行说明](../../docs/setup.md#结构化提取)执行。
确认服务支持严格 JSON Schema，使用可外发的合成政策并确认预算。
逐字段对照原文，记录模型、代码、Prompt、Schema 和结果；Token 或延迟未采集时明确标注。
没有账户或未确认费用时跳过，并写“真实模型未验证”，一次成功不能替代固定质量评估。

## 常见失败

- **接口不支持 Schema**：核对供应商能力，不删除 `response_format` 来假装成功。
- **JSON 合法仍失败**：检查缺键、非整数数值和受约束空白字段，不静默丢弃它们。
- **HTTP 200 却失败**：检查正文、拒绝标记和结束原因；截断不能通过重复请求冒充恢复。
- **业务事实错误却测试通过**：Schema 只验证结构，应增加固定评估而不是宣称程序能识别所有事实错误。

## 验收与下一步

- [ ] 能画出调用链，并说明普通文本请求为什么保持兼容。
- [ ] 独立完成输入上界、嵌套失败和 CLI 变式测试。
- [ ] 能解释输入、解析、领域和 Provider 错误的不同职责。
- [ ] 能证明失败不产生成功 JSON，不吞掉错误或额外调用模型。
- [ ] 如实记录离线验证与真实模型验证的边界，不修改作者日志代表自己的进度。

下一阶段按[项目里程碑](../README.md#4-建议里程碑)建立固定评估与 API；
尚未发布对应课程，不提前引入 Agent 框架。
