# Path to AI Agent Engineer

面向已有软件开发经验的工程师，以 **AI 应用 / Agent 应用工程师**为默认目标，通过渐进式项目，学习构建**可测试、可评估、可恢复、可部署**的 AI Agent 系统。

不以训练基础大模型为目标，也不以掌握某个框架替代工程能力。先使用普通代码和确定性工作流，再判断是否需要 Agent。

## 从这里开始

1. **准备环境**：按[环境指南](./docs/setup.md)完成无 API Key 的离线验证。
2. **开始实践**：进入[第 1～7 课](./projects/baggage-extractor/lessons/README.md)，先预测行为、完成变式，再对照参考实现。
3. **验证掌握**：用[验收指南](./docs/assessment.md#学习推进与项目交付)核对学习证据，判断是否具备进入下一模块的能力。

想先了解全貌，阅读[课程路线](./docs/roadmap.md)。不必先读完所有规划或完成一整年的准备。

## 适合谁

- 会至少一种编程语言，了解 Git、HTTP 和基本自动化测试。
- 不需要机器学习背景；不熟悉 Python 的读者按[前置知识自检](./docs/setup.md#前置知识自检)补课。
- 想从“调用模型成功”进一步走向“可靠地接入真实业务”。

课程目标是让你能独立完成三个层次的工作：**可靠地接入模型 → 构建受控 Agent → 验证恢复与交付能力**。
完成教程不等于获得生产经验，也不保证就业；平台与推理基础设施属于主线之后的选修。

## 课程状态

“可学习”表示有任务、参考实现和离线验收；不表示整个模块或真实模型效果已验收。
实现与验证的区别见[统一状态用语](./docs/assessment.md#实现与验证状态用语)。

| 模块 | 内容 | 状态与入口 |
| --- | --- | --- |
| 00 | 环境与 Python 工程补课 | [第 1 课](./projects/baggage-extractor/lessons/01-project-setup.md)可学习 |
| 01 | 可靠的 LLM 调用 | [第 2～3 课](./projects/baggage-extractor/lessons/README.md)可学习；流式调用尚未实现 |
| 02 | 结构化输出、评估与 API 交付 | [第 4～7 课](./projects/baggage-extractor/lessons/README.md)可学习 |
| 03 | 工具调用、单 Agent 与基础 MCP 接入 | 规划中 |
| 04 | 上下文工程、RAG 与记忆 | 规划中 |
| 05 | 状态与业务流程 | 规划中 |
| 06 | MCP 服务、Skills 与系统集成 | 规划中 |
| 07 | 生产化与综合项目 | 规划中 |

目前只有[行李额提取器](./projects/baggage-extractor)已有 CLI、评估与本地 API 实现，尚无 RAG 或 Agent Loop。
离线验证、真实模型评估和本地 API 冒烟已有[报告摘要](./projects/baggage-extractor/docs/project-report.md)，
但完整逐案例预测与机器可读评分报告尚未归档到仓库，不能仅凭摘要独立复核质量基线，也未宣称质量达标。
Docker 已提供配置但未实机验证；模型实验和部署不阻塞后续概念与离线学习。

## 运行原则

- **离线学习**：测试使用 Stub / HTTP Mock，不需要 API Key，不产生模型费用；首次安装依赖通常需要联网。
- **真实调用**：仅在学习者主动配置并执行时发生，会发送实验文本、单段输入或固定案例并可能计费，详见[配置与费用边界](./docs/setup.md#可选真实模型调用)。
- **质量与安全**：模型输出是不可信输入；单元测试通过不等于模型效果达标；敏感操作必须有权限边界和审批。
- **稳定技术主线**：当前使用 Python 3.13、HTTPX、Pydantic、pytest、Ruff；框架按后续模块需要引入。
- **AI 编程协作**：每个项目完成一次[委派、评审与验证练习](./docs/assessment.md#项目交付与-ai-编程协作)，不以生成代码数量代替理解。

## 参与与记录

仓库按以下职责组织，不以月份划分学习进度：

```text
docs/                         课程路线、环境、验收与参考资料
projects/baggage-extractor/    完整学习项目：lessons、src、tests、evals、docs
templates/                    学习记录、实验与交付模板
```

使用[学习记录模板](./templates/learning-log.md)在自己的 Fork 中保存证据。
改进课程前请阅读[贡献指南](./CONTRIBUTING.md)；课程写作、实验与交付模板从该页按需访问，不是入门必读。

本仓库中由维护者创作的代码和文档按 [Apache License 2.0](./LICENSE) 授权。
第三方材料、数据和商标不因该许可证自动获得授权，仍需按其各自的使用条件处理。
