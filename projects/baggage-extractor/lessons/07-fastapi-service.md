# 第 7 课：FastAPI 服务化与运行边界

上一课：[固定评估与评分](./06-fixed-evaluation.md) · [课程索引](./README.md)

## 目标与前置

建议 3～5 小时。需要完成第 6 课，能解释提取器、Provider、领域 Schema 和模型质量评估的职责。
本课把已有提取能力封装为本地 HTTP API，不增加 Agent Loop，也不把服务裸露到公网。

完成后应能：

- 保持 HTTP 层薄，不复制 Prompt、解析或领域校验。
- 区分存活、配置就绪和真实供应商可用性。
- 将请求、Provider 和模型输出错误映射为稳定且不泄密的 HTTP 契约。
- 复用异步 Provider 连接，并限制单进程模型并发。
- 使用 Stub 验证 API，不让普通 pytest 访问真实模型。

## 接口契约

| 接口 | 行为 | 是否调用模型 |
| --- | --- | --- |
| `GET /health` | Web 进程可以响应 | 否 |
| `GET /ready` | 本地模型配置有效且提取器已创建 | 否 |
| `POST /v1/extractions` | 校验 `text` 并调用 `BaggageExtractor` | 是 |

提取请求只接受一个非空 `text` 字段，沿用 20,000 字符上限并拒绝未知字段。成功结果包含
`request_id` 和完整 `ExtractionResult`。格式正确仍不代表事实正确，应继续使用固定评估集。

## 调用链与生命周期

```text
FastAPI 请求
  → 请求 Schema 与并发门禁
  → BaggageExtractor
  → ModelRequest / Provider
  → 严格 JSON 解析与领域校验
  → API 响应
```

[应用工厂](../src/baggage_extractor/api/app.py)允许测试注入 Stub Extractor。真实服务通过 FastAPI
lifespan 加载配置、创建 Provider，在请求之间复用 HTTP 连接，并在关闭时释放连接。
配置无效时服务仍可回答 `/health`，但 `/ready` 和提取接口返回 503。

## 错误和隐私边界

API 返回稳定的 `error.code`、安全消息和请求 ID：

| 类别 | 状态 | 示例代码 |
| --- | ---: | --- |
| 请求或输入非法 | 422 | `invalid_request` |
| 配置未就绪或并发已满 | 503 | `service_not_ready`、`capacity_exceeded` |
| 模型认证或限流 | 503 | `model_authentication_failed`、`model_rate_limited` |
| 模型超时 | 504 | `model_timeout` |
| 连接、服务端或请求协议失败 | 502 | `model_unavailable`、`model_request_rejected` |
| 非法模型响应、JSON 或领域结构 | 502 | `invalid_model_output` |

客户端错误中不包含 API Key、供应商原始错误、模型正文或政策原文。请求 ID 可由客户端提供；
不满足允许字符和长度时由服务生成 UUID。日志仅记录请求元数据和耗时。

## 并发边界

`API_MAX_CONCURRENT_REQUESTS` 是单进程信号量，默认 4。等待名额超过
`API_ACQUIRE_TIMEOUT_SECONDS`（默认 1 秒）时明确返回 503。
它限制模型并发和意外费用，但不是跨进程队列、用户配额或安全限流。

## 离线练习

在项目目录执行：

Windows / PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api.py tests\test_config.py
.\.venv\Scripts\python.exe -m ruff check .
```

macOS / Linux：

```bash
.venv/bin/python -m pytest tests/test_api.py tests/test_config.py
.venv/bin/python -m ruff check .
```

测试通过 Stub 覆盖健康、就绪、成功提取、输入校验、Provider 错误、非法模型输出、请求 ID
和并发门禁，不读取真实模型响应。

完成以下变式：

1. 提供含空格的请求 ID，证明服务生成新 ID，且响应头和错误正文一致。
2. 让 Stub 抛出模型超时，证明返回 504 而不是空提取结果。
3. 阻塞第一个请求并设置并发为 1，证明第二个请求在等待超时后返回 503。
4. 参照[未就绪测试](../tests/test_api.py)隔离配置：使用 `monkeypatch` 临时移除 `MODEL_*` 环境变量，
   通过 `Settings(_env_file=None)` 获得缺少配置的 `ValidationError`，再替换 API 模块的 `get_settings`
   使其抛出该错误。证明 `/health` 为 200、`/ready` 为 503；同时替换 Provider 构造器为抛出
   `AssertionError` 的函数，证明未创建真实 Provider。不要修改或删除自己的 `.env`，也不更改永久环境变量。

## 可选真实冒烟

按[环境指南](../../../docs/setup.md#fastapi-服务)只绑定 `127.0.0.1`。先请求健康和就绪接口，
再使用无私人信息的合成文本调用一次提取接口。该请求会产生外部传输和潜在费用。

## 验收与下一步

- [ ] 能解释为什么 `/health` 不等于供应商可用或模型质量达标。
- [ ] 能追踪错误类型到 HTTP 状态，且失败不伪造成功结果。
- [ ] 能证明请求日志不包含政策正文或密钥。
- [ ] 能说明单进程并发门禁与生产级限流的差异。
- [ ] 完成离线 API 测试，并将真实模型冒烟标记为已运行或未验证。

完成本课后，按[学习推进条件](../../../docs/assessment.md#学习推进与项目交付)核对证据，可进入模块 03 的概念预习
（该模块尚未发布教程），不必等待真实模型实验或 Docker 验证。
本项目的基础部署与交付另行验收；仓库提供 Dockerfile，但认证、跨进程限流、
故障演练以及当前维护环境的 Docker 实机验证仍未完成。
