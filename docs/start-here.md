# 入门导航

[返回首页](../README.md) · [能力路线](./roadmap.md) · [环境指南](./setup.md)

## 前置知识自检

不必先学一遍机器学习。请确认自己能完成以下任务：

| 自检 | 不熟悉时补什么 | 本仓库练习入口 |
| --- | --- | --- |
| 创建分支、查看 diff、运行测试 | Git 与自动化测试基础 | [第 1 课](../month-01-llm-foundations/lessons/01-project-setup.md) |
| 理解 HTTP 状态码、JSON、环境变量 | API 与配置管理 | [第 2 课](../month-01-llm-foundations/lessons/02-model-calls.md) |
| 看懂类型标注、dataclass、Protocol | Python 对象建模和结构化类型 | [请求与响应契约](../month-01-llm-foundations/src/baggage_extractor/providers/base.py) |
| 看懂 async/await、异常传播 | Python 异步 I/O 和异常处理 | [第 3 课](../month-01-llm-foundations/lessons/03-error-handling.md) |

Python 补课优先参考 [Python 3.13 官方教程](https://docs.python.org/3.13/tutorial/)、[asyncio 文档](https://docs.python.org/3.13/library/asyncio.html)和 [pytest 入门](https://docs.pytest.org/en/stable/getting-started.html)。
围绕当前任务按需阅读，不要求先通读全部文档。

## 先选目标，不把所有岗位都学一遍

默认按 AI 应用工程主线学习。已有后端、前端或平台经验可以继续发挥作用，不必先转成模型训练研究者。
参考[岗位分轨](./career-tracks.md)选择方向；招聘样本只用于理解职责，不是全市场门槛或求职承诺。
先完成共同基础，再按目标岗位加深平台、推理部署或多模态能力。

## 第一轮学习

1. 准备本地仓库，按[环境指南](./setup.md)创建独立虚拟环境并安装项目。
2. 不创建 `.env`，先运行离线测试。理解 Stub 和 HTTP Mock 为什么不等于真实模型。
3. 按[前六课](../month-01-llm-foundations/lessons/README.md)完成“预测行为 → 修改或补充测试 → 验证 → 解释取舍”。
4. 如果有模型账户，再选择执行真实调用；没有账户也能完成前六课的离线练习和评分器校准。
5. 用[学习记录模板](../templates/learning-log.md)留下命令、结果、失败原因和仍未理解的问题。
6. 在项目中选择一个小任务，按[AI 编程协作流程](./coding-agent-workflow.md)练习委派、评审与验证；无需购买指定工具。

建议第一轮的目标是独立跑通离线测试并解释一次调用路径，而不是立即搭建完整 Agent。

## 如何使用参考实现

当前源码覆盖第 1～6 课的参考实现，不是从零开始的空白工程；暂未发布逐课起点标签或独立练习包。
在自己的工作副本或分支中做练习，无需删除参考源码或回退仓库。

- 先阅读课程中的任务与测试要求，自己写出预期结果。
- 运行参考测试确认环境，然后完成课程指定的变式练习。
- 对照源码和提示解释差异；不把“现成测试全绿”当作自己的能力证明。
- 只在自己的 Fork 中保存个人记录；贡献通用改进时移除密钥、私人数据和账户截图。

## 如何判断下一步

- 环境或测试失败：先按[排错表](./setup.md#常见问题)处理，不靠跳过测试继续。
- 测试通过但无法解释：完成本课的复盘问题，再进入下一课。
- 离线验收通过：可以继续理论和工程练习，但记录“真实模型未验证”。
- 当前课程做完：按[第一月计划](../month-01-llm-foundations/README.md)的必做闭环继续探索未实现部分；
  复杂行业规则属于进阶，不需要先凑齐 100 条数据。该计划不是现成可运行教程。

后续模块的规划不应阻碍当前学习，也不应被当成已经存在的功能。
