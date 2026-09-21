# 项目一：可靠的 LLM 应用

[返回课表](../../README.md) · [环境准备](../../docs/setup.md)

把合成行李政策转成经过校验的数据，学习模型调用、结构化输出、评估与失败边界。
这是 LLM 应用，不需要 Agent Loop。先完成第 01～04 课，再进入工具 Agent；
不必先读懂整个适配器、评分器或部署代码。

## 范围与参考实现

第一轮只处理中文单条规则、重量、件数与未知值。完整参考实现还支持多规则和尺寸，
但不要求先穷尽航司业务。原文没有的事实不能补充，结构合法不等于事实正确。
不包含 OCR、抓取、订座、收费、RAG 或 Agent；不能用于真实旅客权益判断。

| 参考入口 | 职责 |
| --- | --- |
| [Provider 契约](./src/baggage_extractor/providers/base.py) | 隔离业务请求与供应商 HTTP 协议 |
| [提取器](./src/baggage_extractor/extractor.py) | 输入、结构化请求、严格 JSON 解析和领域校验 |
| [领域约定](./docs/schema.md) | 完整字段语义、未知值与结构示例，按需查阅 |
| [评估数据](./evals/README.md) | 数据来源、用途和独立性限制 |
| [独立练习](./exercises/extract.py) | 待完成的提取闭环，不影响默认应用与测试 |
| [API](./src/baggage_extractor/api/app.py) | 已有薄 HTTP 层，作为后续服务化参考 |

## 离线运行

按环境指南安装，在本项目目录执行以下 PowerShell 命令。
macOS/Linux 使用 `.venv/bin/python`，并将文件路径的 `\` 换成 `/`。

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest exercises --reference
.\.venv\Scripts\python.exe -m baggage_extractor.evaluation.cli score --dataset evals\datasets\v1\dev.jsonl --predictions evals\examples\dev-predictions-with-errors.jsonl --model scorer-demo --prompt-version not-a-model-run
```

前两个命令验证参考应用；`--reference` 用生产提取器验证同一组练习要求。
评分示例故意含错：6 条案例、1 条失败、3 条完全匹配，完全匹配率 0.5。
这不是模型质量基线。自己的练习用 `pytest exercises` 验证，未实现时应失败。

## 可选真实模型

以下命令会外发输入并可能计费；安装、普通测试和离线评分不需要运行它们。
只使用可外发的合成文本，先在供应商侧设置预算，不提交 `.env` 或原始敏感输出。

仅在 `.env` 不存在时复制配置：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

macOS/Linux：`test -e .env || cp .env.example .env`。
在编辑器中填写[示例配置](./.env.example)，系统环境变量优先于项目 `.env`：

| 配置 | 含义 |
| --- | --- |
| `MODEL_API_KEY` / `MODEL_NAME` | 自己的有效密钥与模型标识，不照抄历史记录 |
| `MODEL_BASE_URL` | HTTP(S) 基础 URL；程序追加 `/chat/completions`，需要 `/v1` 时包含它；不允许内嵌账号密码、查询或片段 |
| `MODEL_STRUCTURED_OUTPUT_MODE` | 默认 `json_schema`；服务只支持 JSON Output 时显式改为 `json_object`，不自动降级 |
| `MODEL_CONNECT_TIMEOUT_SECONDS` / `MODEL_READ_TIMEOUT_SECONDS` | 正的有限数，默认 10 / 30 秒，不是端到端总时限 |
| `MODEL_MAX_RETRIES` / `MODEL_RETRY_BACKOFF_SECONDS` | 额外重试 0～5 次，默认 2；首次退避 0～30 秒，默认 0.5 |
| `API_MAX_CONCURRENT_REQUESTS` / `API_ACQUIRE_TIMEOUT_SECONDS` | 单进程并发 1～100，默认 4；等待名额大于 0 且不超过 60 秒，默认 1 |

适配器使用 Bearer 认证，要求返回 `model` 与非空 `choices[0].message.content`。
`json_schema` 模式要求服务支持严格 Schema；`json_object` 模式仍有本地结构校验，但不把 Schema 发给服务端。
如果提供 `finish_reason`，只接受 `stop`；拒绝和截断不是成功。结束原因缺失时不能据此检测截断。
当前适配器不支持工具调用或流式响应；`LOG_LEVEL` 尚未接入配置。

### 单段提取

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.extract_cli "经济舱可免费托运1件23kg行李。"
```

成功输出 JSON，失败向 stderr 写错误且返回非零退出码。输入上限 20,000 字符，
不是 Token 或费用上限。默认最多 3 次 HTTP 尝试；仍须人工核对字段事实。
当前提取请求未指定输出 Token 上限，没有自动费用熔断，也未采集 Token/费用。

旧文本实验入口 `python -m baggage_extractor.main` 保留兼容：运行三组案例，默认最多 9 次 HTTP 尝试，
只返回未经领域校验的文本与计时。它不是安装检查，不是必修入口，也不是单变量因果实验。

### 固定真实评估

先完成第 03 课。6 条回归案例、默认 2 次重试，最坏请求数为 `6 × (2 + 1) = 18`：

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.evaluation.cli run --dataset evals\datasets\v1\holdout.jsonl --predictions-output evals\runs\candidate-predictions.jsonl --report-output evals\runs\candidate-report.json --confirm-max-requests 18
```

案例数或重试配置变化后重新计算确认值。默认拒绝覆盖输出，确需替换时加 `--overwrite`。
已知调用/解析/校验失败保留在预测与评分分母中；运行结束不代表达到质量门槛。
`evals/runs/` 不入库，分享证据前先检查隐私。

**数据限制：** 当前 6 条开发案例和 6 条原留出案例都只是小型教学数据。
Prompt v2 已参考原留出集失败调优，它现在只用于回归，不能作为独立质量验证。
保留原文件名和 split 仅为兼容；新的独立验证需另外编写、复核和冻结数据。
历史真实运行仅有过摘要，完整预测与评分报告未归档，不以历史分数宣称质量达标。

## 服务化参考，不阻塞后续学习

```powershell
.\.venv\Scripts\python.exe -m uvicorn baggage_extractor.api.app:app --host 127.0.0.1 --port 8000
```

在另一个终端检查 `http://127.0.0.1:8000/health` 与 `/ready`。
前者表示进程可响应，后者只检查本地配置和提取器创建，不探测模型网络或额度。
显式向 `POST /v1/extractions` 发送 `{"text":"经济舱可免费托运1件23kg行李。"}` 才会调用模型并可能计费。

API 包含请求 ID、稳定错误契约和单进程并发门禁；日志不记录原文。
没有认证、分布式限流或费用熔断，不得裸露到公网。

容器配置已提供，尚未实机验证：

```powershell
docker build -t baggage-extractor:local .
docker run --rm --env-file .env -p 127.0.0.1:8000:8000 baggage-extractor:local
```

镜像使用非 root 用户，运行时注入配置；健康检查不调用模型。
扩展练习：运行 `pytest tests/test_api.py`，追踪 HTTP 错误如何对应提取器错误，
再解释为什么重试创建工单还需要幂等，不能照搬只读模型请求的策略。

## 项目验收

- 独立完成第 02 课的提取练习，成功和失败路径均通过测试。
- 能使用固定数据比较结果，区分程序测试、评分器校准和真实模型质量。
- 能预测 401、429、超时和非法正文的重试次数，并用测试证明。
- 完成迁移任务：为“合成报销规则提取”设计金额、币种、适用条件的 Schema，
  至少提供正常、信息缺失、歧义三种输入与期望；实现本地校验测试，解释哪些事实错误仍无法自动识别。
- 用[成果报告](../../templates/project-report.md)记录证据与未验证项。若使用 AI 编程，自行检查 diff 和测试。

以上是进入第 05 课的条件，不要求模型账户、Docker 或真实质量达标。
若宣称真实模型效果，须另附完整预测、评分、版本、事先登记的门槛与适用的数据限制；
若宣称部署完成，须在注明的环境中实际复现。当前项目不代表生产经验。
