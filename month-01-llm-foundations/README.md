# 第一月：LLM 应用基础与行李额提取

面向已有开发基础的学习者，通过一个小范围提取器掌握可靠模型调用、结构化输出与评估，
对应[能力路线](../docs/roadmap.md)的模块 00～02。它是 LLM 应用，不需要 Agent Loop。

## 1. 从哪里开始

1. 按[环境指南](../docs/setup.md)安装项目并运行离线测试。
2. 按[课程索引](./lessons/README.md)完成第 1～7 课的变式练习。
3. 对照[领域契约](./docs/schema.md)解释字段、空值和校验边界。
4. 完成后按[学习推进条件](../docs/assessment.md#学习推进与项目交付)判断下一步；真实模型实验与部署另行验收，
   不阻塞后续学习。第 6 课现有数据用于教学与回归，独立质量验证需新留出集。

课程发布状态统一见[首页](../README.md#课程状态)，个人记录使用[学习记录模板](../templates/learning-log.md)。

### 当前运行入口

| 入口 | 用途 | 验证边界 |
| --- | --- | --- |
| pytest + Stub / HTTP Mock | 离线程序测试 | 不需要密钥，不验证模型质量 |
| `python -m baggage_extractor.main` | 三组文本调用实验 | 真实请求；回答不经过领域校验 |
| `python -m baggage_extractor.extract_cli "政策文本"` | 单段结构化提取 | 真实请求；输出通过领域校验，但不保证事实正确 |
| `python -m baggage_extractor.evaluation.cli score ...` | 对保存的预测离线评分 | 无网络；验证评分与报告，不代表模型质量 |
| `python -m baggage_extractor.evaluation.cli run ...` | 显式运行固定真实模型评估 | 可能计费；保存完整预测和质量报告 |
| `python -m uvicorn baggage_extractor.api.app:app ...` | 本地 FastAPI 服务 | 健康与就绪不调用模型；提取接口会真实调用并可能计费 |

上述 Python 命令需使用项目虚拟环境解释器。完整命令、供应商能力和费用边界只在
[环境指南](../docs/setup.md#可选真实模型调用)维护，不把真实调用当成安装检查。

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

```text
文本实验：main → experiments → ModelRequest → Provider → 文本与计时
结构化提取：extract_cli / FastAPI → BaggageExtractor → ModelRequest → Provider
                                           ↓                         ↓
                                    prompts + models ← JSON 解析与领域校验
```

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
| [Dockerfile](./Dockerfile)、[.dockerignore](./.dockerignore) | 非 root 本地容器入口与构建上下文边界 |

运行依赖和开发工具以[项目配置](./pyproject.toml)为准。当前使用 Python 3.13、HTTPX、
Pydantic、FastAPI、Uvicorn、pytest 和 Ruff；已提供 Dockerfile，但当前维护环境尚未实机验证。
固定数据见[评估目录](./evals)，不提前创建空的部署文件，也不预装尚未使用的框架。

## 4. 建议里程碑

每周可投入 10～15 小时；时间仅供安排，按证据推进，不按日期打卡。
以下保留完整项目的后续目标，不是新增功能承诺。

| 阶段 | 任务 | 完成证据 |
| --- | --- | --- |
| 第 1 周：可靠调用 | 第 1～3 课；配置、契约、异步、错误与重试 | 离线测试和调用路径解释；真实观察可选 |
| 第 2 周：结构化输出与评估 | 第 4～6 课；Schema、提取 CLI、固定数据和评分器 | 变式测试、字段解释、数据用途和评分报告；真实质量另行验证 |
| 第 3 周：API | 第 7 课；`POST /v1/extractions`、`GET /health`、`GET /ready`、错误契约与并发门禁 | 成功、参数错误、模型失败、请求 ID 和并发的 API Stub 测试 |
| 第 4 周：部署与交付（部分完成） | Docker 实机验证、运行指标、认证/限流边界和故障演练 | 本地部署复现、冻结评估报告和交付说明 |

API 第一版接收 `text`，复用 20,000 字符上限并提供明确的错误 Schema。
将认证失败、限流、超时、非法输出与内部错误分开，不将所有失败转成空结果。
日志不默认记录原文；逐步补齐 Prompt/Schema 版本、Token、重试次数与关联 ID。
容器使用非 root 用户、环境变量注入配置，并验证健康与就绪状态。
当前 API 仅用于本地学习与受控验证，尚无认证、分布式限流或经过实机验证的容器部署，勿裸露到公网。
第一月交付证据见[项目报告](./docs/project-report.md)和[FastAPI 协作复盘](./docs/fastapi-collaboration-review.md)。

## 5. 评估数据覆盖

可从 20～30 条合成样例起步；数量不是通过标准。至少覆盖：

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

评分、基线比较、失败分母和门槛遵循[公共验收约定](../docs/assessment.md#结构化提取评估约定)。
非法 JSON、超时、限流等用 Mock 验证，不能混入模型准确率抬高分数。
建议分别报告核心字段匹配、规则拆分、无依据补充、完全匹配及失败计数。
扩展单位或英文能力时单独扩展数据和基线，不把 100 条作为进入下一模块的门槛。

## 6. 必做闭环完成定义

### 学习验收

进入下一模块统一按[学习推进条件](../docs/assessment.md#学习推进与项目交付)判断。
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
- [ ] 使用[交付报告](../templates/project-report.md)说明非模型基线、收益、失败接管与限制，并完成一次[AI 协作练习](../docs/assessment.md#项目交付与-ai-编程协作)。

已有[交付报告](./docs/project-report.md)记录真实运行摘要，不代表上述所有项目已验收；
模型评估完整证据尚未归档，Docker 尚未实机验证。软件测试通过不等于整体模型应用验收，更不等于生产经验。

复盘时回答：为什么需要模型、哪些步骤应确定性执行、哪类失败最重要、
哪次改进有固定数据证据、哪些能力仍未验证。记录使用[学习模板](../templates/learning-log.md)，
不在多个 README 中重复维护个人进度。
