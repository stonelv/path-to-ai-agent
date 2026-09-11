# 环境与运行指南

[返回入门导航](./start-here.md)

## 运行约定

- 教学基线：**Python 3.13**。项目元数据要求 `>=3.13`，不表示更高版本都已验证。
- 以下命令均在 `month-01-llm-foundations` 项目目录执行。
- 使用虚拟环境解释器的完整相对路径，不要求激活环境，也无需修改 PowerShell 执行策略。
- 本轮维护验证环境为 Windows / Python 3.13；macOS/Linux 命令供对应平台使用，尚未在本轮实机验证。
- 当前依赖由 `pyproject.toml` 的版本范围管理，尚无锁文件；不同安装日期可能解析出不同版本。报告问题时附依赖版本。

## Windows / PowerShell

从仓库根目录执行：

```powershell
Set-Location .\month-01-llm-foundations
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

如果已有此项目的可用虚拟环境，直接使用它，无需重建或重复安装。
若没有 `py`，先安装 Python 3.13，或确认 `python --version` 为 3.13 后，用 `python -m venv .venv` 创建环境。

## macOS / Linux

从仓库根目录执行：

```bash
cd month-01-llm-foundations
python3.13 --version
python3.13 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

若系统缺少 `venv` 支持，请按该发行版的 Python 安装文档补齐，不使用全局 `sudo pip install` 替代虚拟环境。

## 离线验证的预期结果

- pytest 退出码为 0，所有测试通过；测试数量会随课程更新，不把固定数量作为验收条件。
- Ruff 输出 `All checks passed!`。
- 不需要 `.env` 或真实 API Key。测试 fixture 临时隔离进程内的 `MODEL_*` 和 `LOG_LEVEL` 环境变量，
  配置测试显式禁用 `.env` 读取；HTTP 测试使用 respx，其他调用使用 Stub。测试后恢复环境，不改磁盘配置。
- 依赖安装可能需要网络，“离线”指测试执行不调用真实模型，并非首次安装可完全断网完成。

这些结果证明当前参考程序的已测行为，不证明模型提取准确率、供应商可用性或部署能力。
不要执行文本实验、提取 CLI 或评估 `run` 子命令来做离线验证：它们都会调用真实模型。
评估 `score` 子命令只读取本地数据与预测，可以离线执行。
每次提交报告实际命令与结果，不把[历史验证记录](../month-01-llm-foundations/PROGRESS.md)的测试数量当作当前基准。

## 可选：真实模型调用

### 先确认边界

当前有三个真实模型入口，均不是 HTTP API 服务：

| 入口 | 发出的内容 | 默认最大 HTTP 尝试数 | 输出 |
| --- | --- | --- | --- |
| `baggage_extractor.main` | 三组[实验文本](../month-01-llm-foundations/src/baggage_extractor/experiments.py) | 整轮 9 次 | 未经领域校验的文本与调用元信息 |
| `baggage_extractor.extract_cli` | 位置参数中的单段政策 | 每次执行 3 次 | 通过领域 Schema 的 JSON |
| `baggage_extractor.evaluation.cli run` | 指定固定数据文件的全部案例 | 案例数 × 3 | 保存逐案例预测和汇总质量报告 |

运行前确认可以将文本发送给你选择的服务；不要使用公司内部或含个人信息的原文。
默认 `MODEL_MAX_RETRIES=2`，表示首次请求之外最多重试 2 次；不可重试错误或重试耗尽会提前终止。
文本实验的输出上限分别为 1000、1500、2500 Token；提取 CLI 和固定评估当前未指定输出 Token 上限，使用供应商默认值。
这些设置不是实际用量或总费用上限。
当前程序没有自动费用熔断，也未采集 Token 用量；先在供应商侧设置预算或额度限制，费用以供应商计费规则为准。

### 配置

仅当项目中没有 `.env` 时，复制示例；不要覆盖已有配置。

Windows / PowerShell：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

macOS / Linux：

```bash
test -e .env || cp .env.example .env
```

在编辑器中填写项目内的 `.env`：

| 变量 | 要求 |
| --- | --- |
| `MODEL_API_KEY` | 自己账户的非空白有效密钥；不要粘贴到 issue、截图或提交中 |
| `MODEL_NAME` | 非空白的真实模型名称，不照抄作者历史记录 |
| `MODEL_BASE_URL` | HTTP(S) 基础 URL，不能含查询参数、片段或账号密码；程序追加 `/chat/completions`，服务要求 `/v1` 时需包含它 |
| `MODEL_STRUCTURED_OUTPUT_MODE` | `json_schema`（默认，服务端严格 Schema）或 `json_object`（仅保证合法 JSON，例如 DeepSeek Chat Completions） |
| `MODEL_CONNECT_TIMEOUT_SECONDS` | 连接超时，必须是大于 0 的有限数值，默认 10 秒 |
| `MODEL_READ_TIMEOUT_SECONDS` | 读取超时，必须是大于 0 的有限数值，默认 30 秒 |
| `MODEL_MAX_RETRIES` | 首次请求之外的重试次数，0～5，默认 2 |
| `MODEL_RETRY_BACKOFF_SECONDS` | 首次退避时间，0～30 秒，默认 0.5；之后指数增加 |

系统环境变量优先于 `.env`。程序按源码位置定位项目内 `.env`，而不是读取任意当前目录的文件。
示例中的 `LOG_LEVEL` 当前尚未接入日志配置，修改它不会改变命令行输出。

### 供应商能力要求

当前适配器要求支持 `POST /chat/completions`、Bearer 认证、`messages`、`temperature`、`max_tokens`，
并返回 `model` 和非空的 `choices[0].message.content`。`x-request-id` 是可选响应头。

结构化提取默认要求支持 `response_format.type=json_schema` 和 `strict=true`。
仅支持 JSON Output 的服务应显式设置 `MODEL_STRUCTURED_OUTPUT_MODE=json_object`；此模式不把
JSON Schema 发给服务端，但仍执行严格 JSON 解析和本地领域校验。不要因为请求失败而自动降级，
否则同一配置的约束强度会在运行间变化。Tool Calling 和流式响应尚未实现。

若响应提供 `finish_reason`，只接受 `stop`；截断、内容过滤、工具调用等不能被当成完整文本。
非空 `refusal` 也视为失败。为兼容现有服务允许结束原因缺失或为 `null`，但这意味着无法据此检测截断，
需要通过真实冒烟核实供应商行为。作者历史实验不是当前兼容性承诺。

### 文本实验

Windows：

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.main
```

macOS / Linux：

```bash
.venv/bin/python -m baggage_extractor.main
```

成功时每组输出案例名称、参数、起止时间、延迟、模型名称、可选请求 ID 和文本回答。
内容和延迟不要求与作者记录一致；当前程序在整轮成功后才打印结果，等待期间没有实时进度输出。
失败时异常向上传播并以非零状态退出，不会伪造成功结果。当前输出不是经领域 Schema 验证的行李额 JSON。

### 结构化提取

输入为非空的单段文本，最多 20,000 字符。使用无私人信息的合成示例：

Windows / PowerShell：

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.extract_cli "经济舱可免费托运1件23kg行李。"
```

macOS / Linux：

```bash
.venv/bin/python -m baggage_extractor.extract_cli "经济舱可免费托运1件23kg行李。"
```

成功时 stdout 只输出符合[领域契约](../month-01-llm-foundations/docs/schema.md)的 JSON，
仍需人工对照原文检查事实。失败时返回非零退出码；配置错误只提示字段名，
输入、解析、领域和 Provider 错误写入 stderr，不返回伪造的空规则。
提取 CLI 当前不输出计时、Token 或费用，不要把文本实验的元信息能力算在它上面。

### 真实模型固定评估

先完成[第 6 课](../month-01-llm-foundations/lessons/06-fixed-evaluation.md)的离线评分练习，
再决定是否运行真实模型。运行器要求显式确认最坏 HTTP 请求数：

```text
案例数 × (MODEL_MAX_RETRIES + 1)
```

默认留出集有 6 条案例、默认重试 2 次，因此最多 18 次：

```powershell
.\.venv\Scripts\python.exe -m baggage_extractor.evaluation.cli run `
  --dataset evals\datasets\v1\holdout.jsonl `
  --predictions-output evals\runs\candidate-predictions.jsonl `
  --report-output evals\runs\candidate-report.json `
  --confirm-max-requests 18
```

macOS / Linux 使用相同参数和 `/` 路径分隔符。配置或数据数量变化后重新计算确认值。
输出路径在任何请求前检查，默认不覆盖已有文件；需要替换时显式增加 `--overwrite`。
本地 `evals/runs/` 被 Git 忽略，防止未经审查的模型输出和错误信息误提交。

已知的 Provider、JSON 和领域错误会保存为失败预测并继续下一案例，不能从报告分母中删除。
报告包含模型配置名称、Prompt、领域 Schema、包版本、最大重试配置、逐案例和平均延迟；
延迟包含 Provider 内部重试。
当前不采集 Token、费用、请求 ID、实际响应模型或重试次数，这些指标应标为“未采集”，不能填 0。
运行前在供应商侧设置预算，结束后人工检查全部失败和成功抽样，再决定是否保存为基线。

## 常见问题

| 现象 | 排查方式 |
| --- | --- |
| Python 版本不满足要求 | 检查虚拟环境解释器版本，使用 3.13；不要只检查全局解释器 |
| `No module named baggage_extractor/pytest/ruff` | 确认当前目录和解释器路径，再在该环境执行 `-m pip install -e ".[dev]"` |
| PowerShell 不允许激活脚本 | 无需激活，直接使用上面的解释器路径 |
| 配置校验失败 | 检查三个必填变量、数值范围，以及系统环境变量是否覆盖 `.env` |
| 401 / 403 | 检查密钥与模型访问权限；认证错误不会重试 |
| 404 或参数不支持 | 检查 Base URL 是否重复追加了 `/chat/completions`，以及模型 API 协议 |
| 429 / 5xx / 超时 | 查看配额、服务状态、网络和重试配置；不要用无限重试处理 |
| HTTP 200 但空正文 | 核对模型行为和输出上限；部分推理模型会消耗预算但没有最终正文，不应视为成功 |
| `did not finish normally` | 检查结束原因和输出上限；截断不会自动重试，不把不完整结果当作成功 |
| JSON / 领域校验失败 | 检查重复键、非标准数值、缺键及类型；不从 Markdown 中猜测 JSON，不静默修复 |
| 评估确认值不匹配 | 用当前案例数乘以最大尝试次数；不要为了绕过检查随意填写 |
| 评估拒绝输出路径 | 使用新的候选文件名，或确认确需替换后显式加 `--overwrite` |
| 长时间没有输出 | 当前入口先完成全部案例再打印；结合超时和重试判断，避免反复启动产生额外费用 |

提交问题时附操作系统、Python 版本、失败命令、脱敏异常和相关依赖版本；不要附完整 `.env`、授权头或敏感模型响应。
