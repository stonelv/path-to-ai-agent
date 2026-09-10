# 第 5 课：首个结构化提取闭环

上一课：[领域 Schema](./04-domain-schema.md) · [课程索引](./README.md)

> **状态：可学习。** 本课已有结构化请求契约、提取服务、独立提取 CLI、
> Stub 与 HTTP Mock 参考测试和离线验收。

## 目标与前置

建议 3～5 小时。需要完成第 4 课，并理解第 2～3 课中的 Provider 协议、HTTP Mock 和异常传播。

本课完成以下闭环：

```text
政策文本
  → 带 JSON Schema 的模型请求
  → JSON 正文
  → Pydantic 领域校验
  → ExtractionResult
```

完成后应能：

- 使用供应商无关契约请求结构化输出。
- 将模型正文解析为第 4 课的领域结果。
- 区分输入错误、JSON 解析错误、领域校验错误和 Provider 错误。
- 使用 Stub 和 HTTP Mock 完成不访问真实模型的测试。

本课不实现 FastAPI、RAG、Agent Loop，也不建立完整模型质量评估器。

## 设计边界

- Provider 负责传输、供应商协议和响应结构校验。
- Extractor 负责行李业务 Prompt、JSON 解析和领域校验。
- 领域模型不依赖 HTTP 或具体供应商。
- 普通文本调用必须保持兼容。
- 不支持结构化输出时明确失败，不能静默忽略 Schema。
- 严重损坏的 JSON 不通过正则修复后伪装成功。

## 动手任务

### 1. 先修正认证边界

开始结构化调用前，检查[OpenAI 兼容适配器](../src/baggage_extractor/providers/openai_compatible.py)。
当前实现若仍把固定掩码字符串作为 `Authorization` 头，就必须先改成读取 `Settings.model_api_key` 的真实值：

```text
Authorization: Bearer <configured API key>
```

同时更新 HTTP Mock：

- 仅使用 `test-key`。
- 断言发送 `Bearer test-key`。
- 不在日志、异常或测试失败消息中打印真实密钥。

掩码用于日志展示，不能代替真实请求认证。

### 2. 扩展供应商无关请求契约

修改[请求契约](../src/baggage_extractor/providers/base.py)，增加可选的结构化输出描述，例如：

```text
StructuredOutputSpec
├── name
├── description
├── json_schema
└── strict
```

并在 `ModelRequest` 中加入：

```text
structured_output: StructuredOutputSpec | None
```

建议 `json_schema` 使用能安全序列化的明确映射类型，不把 Pydantic 模型类直接传到 HTTP 层。
普通文本请求的默认值为 `None`，保持第 2～3 课行为。

### 3. 扩展 OpenAI 兼容适配器

修改[适配器](../src/baggage_extractor/providers/openai_compatible.py)：

- 普通请求不携带结构化输出参数。
- 结构化请求按当前协议发送严格 JSON Schema。
- 仍返回通用 `ModelResponse`，不返回供应商 SDK 对象。
- 不在 Provider 层导入行李领域模型。
- 供应商拒绝不支持的参数时，沿用明确的请求错误，不静默退化为普通文本。

不同“OpenAI 兼容”服务对结构化输出支持不同。实现和测试只承诺当前明确采用的 payload；
真实供应商兼容性通过可选冒烟测试验证。

### 4. 定义版本化 Prompt

新增：

```text
src/baggage_extractor/prompts.py
```

保存显式版本，例如：

```python
PROMPT_VERSION = "baggage-extraction-v1"
```

Prompt 至少要求：

- 只依据输入文本。
- 严格输出航司信息、免费托运行李数组和随身行李数组。
- 缺失的可空字段返回 `null`；`note` 和 `special_notes` 没有内容时返回空字符串。
- 未提供舱位代码时返回 `fare_codes: []`。
- 免费托运行李写入 `free_baggage_rules`，随身行李写入 `baggage_rules`。
- 无对应政策时返回相应的空数组。
- `pieces` 输出非负整数；明确以 cm 给出的长宽高输出非负整数。
- 同时存在最小和最大尺寸时数值字段取最大尺寸，`note` 保留完整限制。
- 公斤重量使用紧凑的 `kg` 表示，不进行跨单位数值换算。
- 不输出 JSON 之外的解释。

Prompt 不能替代 JSON Schema、权限或程序校验。

### 5. 实现提取服务和异常

建议新增：

```text
src/baggage_extractor/extractor.py
src/baggage_extractor/errors.py
```

`BaggageExtractor` 通过构造函数接收 `ModelProvider`，建议流程：

```text
extract(text)
  1. 校验文本非空和长度上限
  2. 构造消息、Prompt 版本和 JSON Schema
  3. 调用 ModelProvider
  4. 解析响应正文为 JSON
  5. 使用 ExtractionResult 校验
  6. 返回结构化结果
```

定义并区分：

```text
ExtractionError
├── InvalidExtractionInputError
├── StructuredOutputParseError
└── StructuredOutputValidationError
```

具体命名可以按代码风格调整，但必须区分：

- 输入为空或超长。
- 正文不是合法 JSON。
- JSON 合法但不满足领域 Schema。
- Provider 的认证、限流、连接和超时错误。

Provider 异常继续保留原类型，不统一包装成模糊的“提取失败”。

`extractor.py` 不应：

- 直接创建 HTTP 客户端或读取 API Key。
- 捕获宽泛异常并返回空列表。
- 删除非法字段后继续返回成功。
- 使用正则修复严重损坏的 JSON。

### 6. 使用 Stub 测试提取器

新增：

```text
tests/test_extractor.py
```

Stub 应记录收到的 `ModelRequest`，便于断言 Prompt、Schema 和版本。

至少覆盖：

1. 单规则成功。
2. 免费托运行李和随身行李进入不同数组。
3. 无关文本返回两个空规则列表。
4. 缺少航司信息保留 `null`。
5. 缺少舱位代码返回空数组。
6. 非法 JSON 明确失败。
7. 合法 JSON 中缺失必填键时明确失败。
8. 空白文本字段明确失败。
9. Provider 限流或超时异常不被吞掉。
10. 请求包含正确 JSON Schema 和 Prompt 版本。
11. 返回值不泄漏 Provider 或 HTTP 响应对象。

空正文已由 Provider 拒绝；Extractor 测试可以使用异常 Stub 验证该错误会继续传播，不必重复模拟 HTTP 解析细节。

### 7. 扩展 HTTP Mock 测试

更新现有[适配器测试](../tests/test_openai_compatible_provider.py)，覆盖：

- 结构化输出 payload 正确。
- 普通文本调用不携带结构化参数。
- 认证头使用 `Bearer test-key`。
- 错误输出不包含测试密钥。
- 结构化输出请求被供应商拒绝时有明确错误。
- 第 2～3 课已有成功、空正文、分类和重试测试继续通过。

### 8. 新增独立提取 CLI

当前[实验入口](../src/baggage_extractor/main.py)用于运行三组参数实验，不将其改成另一种职责。

新增：

```text
src/baggage_extractor/extract_cli.py
tests/test_extract_cli.py
```

第一版 CLI：

- 从位置参数接收文本。
- 调用 `BaggageExtractor`。
- 输出格式化 JSON。
- 失败时写入标准错误并返回非零退出码。
- 不在输出中显示 API Key 或完整内部响应。

CLI 测试注入 Stub，不访问真实模型。

真实调用示例：

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.extract_cli "经济舱可免费托运1件23kg行李。"
```

### 9. 可选真实模型冒烟测试

只有离线测试和 Ruff 全部通过后才执行：

1. 阅读[真实调用边界](../../docs/setup.md#可选真实模型调用)。
2. 使用一段不含私人信息的合成中文政策。
3. 确认所选服务支持当前结构化输出参数。
4. 验证结果通过 Pydantic，并确认两类行李进入正确数组。
5. 记录模型、Prompt、Schema 版本、延迟、Token/成本可用性和失败。

没有账户或未获费用确认时跳过，并记录“真实模型未验证”。
一次成功不等于完成模型质量评估；供应商不兼容时记录限制，不删除 Schema 或自动修复 JSON 来绕过。

## 运行与预期

在项目目录运行以下离线验收：

Windows / PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

macOS / Linux：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

常规测试不得要求 `.env` 或真实 API Key，也不能发起真实模型请求。

<details>
<summary>实现提示</summary>

- 先写领域和 Extractor 的 Stub 测试，再修改 HTTP payload。
- 保留 `ModelRequest` 新字段的默认值，避免破坏现有构造代码。
- Pydantic 提供 JSON Schema 和最终业务校验；两次验证服务于不同信任边界。
- 使用 `json.loads` 或 Pydantic JSON 校验处理完整正文，不从 Markdown 代码块中猜测并抽取 JSON。
- 输入长度上限使用一个命名常量并写测试，具体值在实现时结合模型和费用边界确定。

</details>

## 常见问题

- **Provider 直接返回 `ExtractionResult`：**会把通用模型边界与行李业务耦合。
- **模型返回非法结果时返回空列表：**无法区分“无行李政策”和“提取失败”。
- **只验证 JSON Schema：**仍需通过 Pydantic 和固定评估集检查业务结果。
- **静默删除结构化参数：**会让调用方误以为获得了严格输出保证。
- **为了测试写真实 `.env`：**常规测试应注入 Settings、Stub 或 HTTP Mock。
- **把一次冒烟成功写成准确率结论：**模型质量需要固定数据集和重复评估。

## 验收与交付

- [x] 普通文本模式的既有测试保持通过。
- [x] 结构化请求通过供应商无关契约表达。
- [x] Extractor 明确区分输入、解析和领域错误。
- [x] 免费托运行李与随身行李没有混用，字段类型和空值规则符合最终 Schema。
- [x] Provider 错误类型能够传播。
- [x] API Key 用于真实认证，但不会进入日志或提交内容。
- [x] 新 CLI 与测试不修改实验入口职责。
- [x] 完整 pytest 与 Ruff 通过，常规测试没有网络调用。
- [x] 真实冒烟测试是显式可选的，并记录验证边界。
- [x] 更新 `docs/schema.md`、课程状态和作者进度；没有真实验证时不宣称完成。

建议独立提交：

```text
Implement structured extraction pipeline
```

完成本课后，下一阶段是小型固定评估集和 API 服务化；不要提前引入 Agent 框架。
