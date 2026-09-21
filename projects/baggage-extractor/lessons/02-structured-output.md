# 第 02 课：结构化输出与校验

上一课：[模型调用](./01-model-calls.md) · [返回课表](../../../README.md) · 下一课：[评估](./03-evaluation.md)

前置：第 01 课、基础类型与异常。建议 2～3 小时。

## 问题与必要概念

本课完成 `原文 → Schema 请求 → JSON → 本地校验 → 结果`。
只使用单条规则；沿用完整领域模型，暂不扩展复杂航司政策。

- JSON 合法不等于字段合法；字段合法不等于来自原文。
- `null` 是未知，`0` 是明确零额度，`[]` 是没有规则，不能互相代替。
- Schema 描述结构，Prompt 描述提取约定，事实正确性由评估检查。
- Provider 负责通信；提取器不应读取密钥、重复 HTTP 重试或悄悄修补模型输出。

## 动手任务

起点是[exercises/extract.py](../exercises/extract.py)，只修改这个文件，不删除或改弱验收测试。
先运行下面的练习命令，确认 `NotImplementedError`，再实现：

1. 拒绝空白和超过 20,000 字符的输入，Provider 不得被调用。
2. 用[已有 Prompt 构造器](../src/baggage_extractor/prompts.py)和
   [领域模型](../src/baggage_extractor/models.py)构造温度为 0 的严格 Schema 请求。
   使用已有结构化输出名称与描述，不手工复制 Schema。
3. 调用 Provider 一次，使用[严格 JSON 解析](../src/baggage_extractor/json_utils.py)；
   解析失败映射为 `StructuredOutputParseError`。
4. 将数据校验为 `ExtractionResult`，校验失败映射为 `StructuredOutputValidationError`。
   Provider 错误原样传播，不返回空成功结果。

在自己的测试中增加“件数为字符串”的案例，解释为什么不自动转换成整数。

## 运行与预期

在项目目录执行；macOS/Linux 用 `.venv/bin/python`：

```powershell
.\.venv\Scripts\python.exe -m pytest exercises
.\.venv\Scripts\python.exe -m pytest exercises --reference
```

第一个命令只验收自己的练习，初始状态故意失败，实现后应全部通过。
第二个命令用生产提取器运行同一组验收，初始即应通过，不会填好自己的答案。
普通 `pytest` 仍只运行参考应用测试。两个命令都不调用模型。

## 一个失败案例

返回 `{"airline_code": null}` 是合法 JSON，但缺少其他必填字段，应产生领域校验错误。
返回 Markdown 包裹的 JSON 应产生解析错误。两者都不能被改成“没有行李规则”。

## 验收

- 独立实现练习，合法输入只调用一次 Provider，非法输入零次。
- 证明 20,000 / 20,001 字符边界、解析失败、领域失败与 Provider 失败的行为。
- 证明请求包含生成的 Schema 和原文，不靠硬编码结果通过测试。
- 解释“校验通过但补出了不存在的航司”为什么仍是错误。

## 可选深入

<details>
<summary>提示与参考实现</summary>

复用 `build_extraction_messages`、`StructuredOutputSpec`、`loads_strict_json` 和
Pydantic 的 `model_validate`，只捕获需要转换的两类异常。
完成自己的尝试后再对照[参考提取器](../src/baggage_extractor/extractor.py)。
完整字段定义见[领域契约](../docs/schema.md)，暂不要求实现单位换算、多规则匹配或 API。

</details>
