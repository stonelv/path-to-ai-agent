# 课程调整依据

[能力路线](./roadmap.md) · [岗位分轨](./career-tracks.md)

研究基准日：**2026-09-10**。下列内容为公开原文核验后的摘要，不是全市场统计，也不保证覆盖截至该日的全部最新发布。
技术资料用于判断能力与设计方向，招聘需求只依据 JD；“前移某一课”等顺序安排是本仓库的教学判断。

## 官方技术资料

| 资料 | 日期性质 | 本仓库采用的结论 |
| --- | --- | --- |
| [Anthropic：Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | 发布 2025-09-29 | 上下文有限，需要筛选、压缩、按需加载与隔离；增加模块 04 专项实验 |
| [Anthropic：Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | 发布 2026-01-09 | 区分任务、trial、轨迹与最终环境结果；模块 03 起增加 Agent 验收 |
| [Anthropic：Managed Agents 架构](https://www.anthropic.com/engineering/managed-agents) | 发布 2026-04-08 | 运行与状态、执行环境需要明确边界；保留恢复、隔离与故障测试，不要求照搬厂商架构 |
| [Anthropic：Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | 发布 2025-10-16；页面标注更新 2025-12-18 | 任务知识与资源可渐进式加载；增加 Skill 封装与安全审查 |
| [Anthropic：Long-running agent harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | 发布 2025-11-26 | 小步实现、环境反馈、Git 与端到端验收；引入 AI 编程协作任务 |
| [MCP 架构](https://modelcontextprotocol.io/specification/2025-11-25/architecture)与[安全实践](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices) | 2025-11-25 是规范版本标识 | 基础 client 与受控 server 分阶段学习，权限由代码与凭据边界实施 |
| [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)与[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | 滚动文档，未核实更新日期 | 区分线程持久状态与跨线程信息；恢复节点时注意副作用幂等 |
| [OpenAI Agents SDK Models](https://openai.github.io/openai-agents-python/models/)与[Tracing](https://openai.github.io/openai-agents-python/tracing/) | 滚动文档，未核实更新日期 | 跨供应商能力需验证，Trace 需要数据脱敏；不能把观测当作质量验收 |
| [vLLM Online Serving](https://docs.vllm.ai/en/stable/serving/online_serving/) | 滚动文档，未核实更新日期 | 推理服务与容量优化作为岗位选修，不作为应用学习起点 |

这些资料存在厂商和任务偏向，课程应通过实验验证取舍，不照搬其性能数字，也不把访问日期当成发布日期。
没有证据要求所有项目都采用多 Agent、长期记忆或微调；需要先说明问题和额外复杂度的收益。

## 招聘样本

共核验中国 3 条、国际 3 条。A 表示雇主官方招聘平台，B 表示第三方招聘正文，尚未获得雇主官网同岗位复核。
页面可访问不等于仍在招聘；官方招聘页日期为 HTML 中的 `datePosted`，不是最后更新时间。

| 公司与职位 | 地区与日期 | 核实的要求摘要 | 来源权重与限制 |
| --- | --- | --- | --- |
| [字节跳动：Agent 开发工程师](https://www.nowcoder.com/jobs/detail/430944) | 北京；发布日期未核实 | Python/Go、服务交付、数据库/缓存/消息队列、性能稳定性、多模态应用；RAG/框架/容器经验为加分 | B，社招；页面“2026最新”不是发布时间 |
| [阿里巴巴：AI agent 应用研发工程师](https://www.nowcoder.com/jobs/detail/440241) | 杭州；投递窗口 2026-03-19 至 2026-04-15 | 业务归因、记忆、工具、RAG、评测/Trace、异步降级、AI coding | B，面向 2027 届的实习；窗口已过，不用作有经验转岗者的社招门槛 |
| [智启心源：AI Agent 工程师](https://www.nowcoder.com/jobs/detail/400166) | 上海；发布日期未核实 | Agent 模块、Prompt、评估、部署迭代、前后端 owner 经验、模型部署优化 | B，社招；兼有模型优化职责，不是纯训练研究岗 |
| [OpenAI：Applied AI Engineer, Agent Enablement](https://jobs.ashbyhq.com/openai/c1a28411-266b-487b-8ef3-03efb254fc36) | 旧金山；2026-07-21 | 4～6 年工程经验、全栈/API/连接器、MCP/CLI、身份权限、评测、灰度与维护 | A，完整正文与日期在页面 HTML 中核实；非入门岗位样本 |
| [Supabase：AI Platform Engineer](https://jobs.ashbyhq.com/supabase/3b5d54ca-741b-45ac-bd3f-31605a0d3541) | 全球远程；2026-07-31 | 生产 Agent、队列、持久状态、审批回滚、评测 CI、MCP、权限与成本治理 | A，偏独立承担平台；远程不自动等于任何地区均可雇佣 |
| [Brain Co.：AI Platform Engineer, Infrastructure](https://jobs.ashbyhq.com/brainco/2a423180-afac-4bad-becd-d80939be735f) | 旧金山/美国境内远程元数据；2025-09-29 | 5 年以上后端/基础设施、Kubernetes、IaC、网络、SLO、事故响应和推理服务 | A，资深基础设施方向；具体工作地点需招聘方确认 |

国内官方动态页面未取得可读的完整 JD，因此没有用搜索摘要冒充官方招聘正文。
国际样本偏资深与 AI 原生企业，国内样本少且含过期实习，不能推断岗位占比、薪资趋势或统一转岗门槛。

## 据此做出的课程调整

- 保留可靠调用、结构化输出、RAG、工具、状态恢复与生产化主干。
- 将上下文与记忆列为显式任务，基础 MCP client 前移到工具学习阶段。
- 为 Agent 增加轨迹约束、业务终态、恢复、安全和成本验收；每个项目练习 AI 编程协作。
- 应用工程为默认主线，平台与推理基础设施分轨，不把所有 JD 技术项都设为必修。
- 缩小第一月业务范围、取消固定样本数作为唯一通关门槛，是教学负荷判断，不是招聘统计结论。

后续修订应更新核验日期和来源限制，保留“来源事实”与“课程建议”的区别，不只追逐新框架名称。
