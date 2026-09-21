# 第 04 课：让调用可靠

上一课：[评估](./03-evaluation.md) · [返回课表](../../../README.md) · 下一课：[工具契约](../../tool-agent/lessons/05-tool-contracts.md)

前置：第 03 课、异常传播。建议 1～2 小时。不要求重写通用 Provider。

## 问题与必要概念

外部模型不可用时，程序必须明确失败且停止。增加重试不能修复错误凭据，也不保证业务只执行一次。

| 情况 | 当前行为 |
| --- | --- |
| 401 / 403 | `AuthenticationError`，不重试 |
| 429 / 5xx | 限流 / 服务错误，有限重试 |
| HTTPX 超时、已映射网络错误 | 有限重试，耗尽后显式失败 |
| 其他 4xx、非法正文、空内容、明确拒绝或异常结束原因 | 不重试 |

默认额外重试 2 次，因此最多调用 3 次；退避为 0.5、1.0 秒，最终失败后不再等待。
连接/读取超时不等于端到端 deadline。当前没有 jitter、`Retry-After` 处理或费用熔断。
读超时不证明服务端没有执行，重试可能重复计算并产生费用。

## 动手任务

1. 先预测连续 401、连续 429、429 后成功、连续读取超时、首次空正文的异常与调用次数。
2. 对照[适配器测试](../tests/test_openai_compatible_provider.py)，只追踪上述路径。
3. 在 HTTP 错误参数化测试中补充 403，断言 `AuthenticationError`、1 次调用且不退避。
4. 增加“第一次连接失败，第二次成功”的测试；验证次数与结果，不只断言最终成功。
5. 解释为什么“创建工单成功但响应丢失”不能直接套用同样的重试策略，指出需要的幂等边界。

## 运行与预期

在项目目录执行，macOS/Linux 替换解释器与文件路径：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_openai_compatible_provider.py tests\test_config.py
.\.venv\Scripts\python.exe -m ruff check .
```

参考测试与新增测试通过，不调用模型。连续 429 / 读取超时最多 3 次，429 后成功 2 次，
401 / 403 / 非法正文 1 次。退避测试替换等待函数，不真实休眠。

## 一个失败案例

“重试次数设为 2，所以应该调用 2 次”是错误的。写清首次请求与额外重试的关系，
再用 `MODEL_MAX_RETRIES=0` 验证可重试错误也只请求一次。不要改断言掩盖次数问题。

## 验收

- 能预测错误类型、调用次数与停止条件，并用离线测试验证。
- 完成 403 与连接恢复测试，不吞掉异常或无限等待。
- 能区分请求超时、总运行时限、请求次数与费用上限。
- 完成[项目一验收与迁移任务](../README.md#项目验收)，记录未验证项，再进入第 05 课。

## 可选深入

阅读[HTTPX 超时](https://www.python-httpx.org/advanced/timeouts/)和
[参考适配器](../src/baggage_extractor/providers/openai_compatible.py)。
API、Docker 和评分器内部算法不阻塞工具 Agent 学习，已有入口保留在[项目说明](../README.md)。
