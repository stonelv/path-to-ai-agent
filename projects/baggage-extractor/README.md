# 项目一：航司行李额提取器

面向已有开发基础的学习者，通过一个小范围提取器掌握可靠模型调用、结构化输出与评估，
对应[课程路线](../../docs/roadmap.md)的模块 00～02。它是 LLM 应用，不需要 Agent Loop。
课程、源码、测试和评估数据放在同一项目中；项目名称不绑定月份或课程模块编号。

## 1. 从哪里开始

学习顺序和任务统一见[课程索引](./lessons/README.md)，安装与运行见[环境指南](../../docs/setup.md)。
本页只说明项目范围、架构与交付要求；课程发布状态见[首页](../../README.md#课程状态)。

### 当前运行入口

| 入口 | 用途 | 验证边界 |
| --- | --- | --- |
| pytest + Stub / HTTP Mock | 离线程序测试 | 不需要密钥，不验证模型质量 |
| `python -m baggage_extractor.main` | 教学入口：三组文本调用实验，不是完整提取应用 | 真实请求；回答不经过领域校验 |
| `python -m baggage_extractor.extract_cli "政策文本"` | 单段结构化提取 | 真实请求；输出通过领域校验，但不保证事实正确 |
| `python -m baggage_extractor.evaluation.cli score ...` | 对保存的预测离线评分 | 无网络；验证评分与报告，不代表模型质量 |
| `python -m baggage_extractor.evaluation.cli run ...` | 显式运行固定真实模型评估 | 可能计费；保存完整预测和质量报告 |
| `python -m uvicorn baggage_extractor.api.app:app ...` | 本地 FastAPI 服务 | 健康与就绪不调用模型；提取接口会真实调用并可能计费 |

上述 Python 命令需使用项目虚拟环境解释器。完整命令、供应商能力和费用边界只在
[环境指南](../../docs/setup.md#可选真实模型调用)维护，不把真实调用当成安装检查。

## 2. 项目范围

### 2.1 项目名称

航司行李额结构化提取器（Airline Baggage Allowance Extractor）。

### 2.2 业务问题

把政策文字中的免费托运行李和随身行李规则转换为可验证的数据。
学习重点是供应商隔离、不可信输出校验和失败处理，不是穷尽所有航司业务。
真实收费、订座或旅客权益判断不能直接依赖本教学实现。

### 2.3 输入

第一版主要使用无私人数据的中文合成政策。输入必须非空，当前上限为 20,000 字符。
字符上限不是 Token 上限，也不是费用上限。

### 2.4 输出

字段含义、单位、空值规则与输入/输出示例统一见[领域契约](./docs/schema.md)。
JSON Schema 从[模型代码](./src/baggage_extractor/models.py)生成，不手工维护第二份。
格式正确不等于提取正确：原文没给航司代码就不能补出代码，明确给出件数就不能标为未知。

### 2.5 第一版范围

**必做闭环的目标（不等于当前已实现）：**

以下是完整项目的目标，不是进入模块 03 的全部前置条件；学习推进与交付分别验收。

- 提取航司信息、舱位说明和舱位代码，区分免费托运与随身行李。
- 保留公斤重量的 kg 表达、非负整数件数、cm 尺寸和说明；未知值按领域契约表达。
- 对结构、输入和失败路径执行确定性校验。
- 使用小型固定评估集建立回归基线；独立质量验收另建未用于调优的留出集。提供提取 API 与本地基础部署。
- 覆盖无关文本、缺失信息、明确零额度、多规则与超范围条件，不静默套用普通规则。

**进阶扩展，不阻塞必做验收：**

- 英文、儿童/会员条件、复杂票价品牌、会员叠加和政策冲突。
- kg/lb、cm/inch 换算；保留原值和转换依据。
- 更大评估集、流式交互、并发与成本优化。

**不纳入本项目：** OCR、自动抓取、订座、超额费用计算、RAG 和多 Agent。
不要为了达到某个数据条数或覆盖所有行业规则，长期推迟后续工具调用学习。

## 3. 当前代码如何组织

| 入口类型 | 调用路径 |
| --- | --- |
| 教学文本实验 | `main → experiments → Provider → 文本与计时`；观察模型行为，不执行领域校验 |
| 业务提取 | `extract_cli / FastAPI → BaggageExtractor → Provider → JSON 解析与领域校验`；复用 Prompt 与模型契约 |
| 离线评分 | `evaluation.cli score → 加载案例与预测 → scorer → 报告`；不调用模型 |
| 真实评估 | `evaluation.cli run → BaggageExtractor → 保存预测 → scorer → 报告`；显式确认请求数量 |

`main` 保留既有实验命令兼容性，不是以上入口的总调度器。

| 位置 | 单一职责 |
| --- | --- |
| [config.py](./src/baggage_extractor/config.py) | 加载与校验配置；密钥不进入业务结果 |
| [providers/base.py](./src/baggage_extractor/providers/base.py) | 供应商无关的请求、响应和 Protocol |
| [providers/openai_compatible.py](./src/baggage_extractor/providers/openai_compatible.py) | HTTP、响应协议、错误映射和有限重试 |
| [models.py](./src/baggage_extractor/models.py) | 领域类型与 JSON Schema，不依赖模型或网络 |
| [prompts.py](./src/baggage_extractor/prompts.py) | 版本化提取指令 |
| [extractor.py](./src/baggage_extractor/extractor.py) | 输入校验、结构化请求、JSON 解析和领域校验 |
| [extract_cli.py](./src/baggage_extractor/extract_cli.py) | 参数、输出、退出码；可注入测试 Provider |
| [evaluation](./src/baggage_extractor/evaluation) | 案例/预测契约、JSONL 加载、确定性评分和评估 CLI |
| [api](./src/baggage_extractor/api) | FastAPI 生命周期、HTTP 契约、错误映射、请求 ID 与并发门禁 |
| [main.py](./src/baggage_extractor/main.py)、[experiments.py](./src/baggage_extractor/experiments.py)、[telemetry.py](./src/baggage_extractor/telemetry.py) | 实验编排、案例与计时 |
| [tests](./tests) | 对应职责的离线回归 |
| [Dockerfile](./Dockerfile)、[.dockerignore](.dockerignore) | 非 root 本地容器入口与构建上下文边界 |

运行依赖和开发工具以[项目配置](./pyproject.toml)为准。当前使用 Python 3.13、HTTPX、
Pydantic、FastAPI、Uvicorn、pytest 和 Ruff；已提供 Dockerfile，但当前维护环境尚未实机验证。
固定数据见[评估目录](./evals)，不提前创建空的部署文件，也不预装尚未使用的框架。

## 4. 运行与已知限制

API 使用现有提取器、稳定错误契约、请求 ID 与单进程并发门禁；日志不默认记录原文。
当前仅用于本地受控验证，尚无认证、分布式限流或费用熔断，勿裸露到公网。
容器配置使用非 root 用户和环境变量注入，但尚未实机验证；Token 和实际重试次数尚未采集。
历史运行与未完成项见[项目报告](./docs/project-report.md)，协作证据见[FastAPI 复盘](./docs/fastapi-collaboration-review.md)。

## 5. 评估数据覆盖

当前数据包含 6 条开发案例和 6 条原留出案例，均为中文合成文本，仅用于小型教学与回归，
不具统计代表性。实际用途见[数据说明](./evals/README.md#当前用途与限制)，覆盖目标如下：

| 场景 | 需要核对的结果 |
| --- | --- |
| 简单单规则 | 舱位、重量、件数正确 |
| 免费托运与随身行李 | 分别进入对应数组，不跨类别复制 |
| 信息缺失与明确零额度 | 区分 `null`、空数组、空说明和 `0` |
| 多舱位规则 | 相同额度保留并列条件，不同额度拆分 |
| 尺寸 | 长宽高、最大/最小值、三边之和不混淆 |
| 无关文本 | 不臆造规则，两个数组仍存在 |
| 超范围或歧义条件 | 明确暴露限制，不冒充普通规则；当前 Schema 不能自动检测这类错误 |

样例需有 ID、期望结果、来源/合成标记、覆盖标签和版本。
同源或近重复数据不要跨开发集与留出集。加入真实资料前核对使用与再分发条件，
不要提交旅客姓名、票号、证件或联系方式。

评分、基线比较、失败分母和门槛遵循[公共验收约定](../../docs/assessment.md#结构化提取评估约定)。
非法 JSON、超时、限流等用 Mock 验证，不能混入模型准确率抬高分数。
建议分别报告核心字段匹配、规则拆分、无依据补充、完全匹配及失败计数。
扩展单位或英文能力时单独扩展数据和基线，不把 100 条作为进入下一模块的门槛。
当前仍缺少独立的新留出集，超范围与歧义条件的系统覆盖也待补充；不为凑数量增加重复的简单案例。

## 6. 必做闭环完成定义

### 学习验收

进入下一模块统一按[学习推进条件](../../docs/assessment.md#学习推进与项目交付)判断。
完成前七课的离线任务与解释即可核对前置能力；没有模型账户或 Docker 不阻塞继续学习。
模块 03 尚未发布教程，达到前置条件不表示已有下一组可运行课程。

### 完整项目交付

以下项目与学习验收分开记录，未执行项保留“未验证”，不能用离线测试替代：

- [ ] 已通过学习验收，并记录验证范围和未验证项。
- [ ] 关键覆盖矩阵有评分规则、新冻结且未用于调优的留出集、预先登记的质量门槛和失败分析；v1 原留出集仅用于教学与回归。
- [ ] 已执行真实模型评估，归档完整逐案例预测、评分报告和版本信息，记录是否达到预先登记的门槛；运行完成不等于质量通过。
- [ ] API 有请求、响应、错误契约及离线回归，不要求密钥才能运行程序测试。
- [ ] 从新环境能复现安装、本地容器启动、健康检查和显式启用的真实冒烟。
- [ ] 报告质量、延迟、可采集的 Token/费用及版本；未采集项不填 0，未验证项不冒充通过。
- [ ] 使用[交付报告](../../templates/project-report.md)说明非模型基线、收益、失败接管与限制，并完成一次[AI 协作练习](../../docs/assessment.md#项目交付与-ai-编程协作)。

已有[交付报告](./docs/project-report.md)记录真实运行摘要，不代表上述所有项目已验收；
模型评估完整证据尚未归档，Docker 尚未实机验证。软件测试通过不等于整体模型应用验收，更不等于生产经验。

复盘时回答：为什么需要模型、哪些步骤应确定性执行、哪类失败最重要、
哪次改进有固定数据证据、哪些能力仍未验证。记录使用[学习模板](../../templates/learning-log.md)，
不在多个 README 中重复维护个人进度。
