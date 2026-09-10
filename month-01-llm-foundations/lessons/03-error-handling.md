# 第 3 课：异步、错误分类与有限重试

上一课：[模型调用](./02-model-calls.md) · [课程索引](./README.md) · 下一课：[领域 Schema](./04-domain-schema.md)

## 目标与前置

建议 2～3 小时。需要完成第 2 课，理解异常传播和 `await`。
本课要证明“外部服务失败时程序的行为仍可预测”，不是通过无限重试让演示偶尔成功。

## 当前策略

| 失败 | 映射的异常 | 自动重试 |
| --- | --- | --- |
| 401 / 403 | AuthenticationError | 否 |
| 429 | RateLimitError | 是，有次数上限 |
| 5xx | ServerError | 是，有次数上限 |
| 其他 4xx | InvalidRequestError | 否 |
| HTTPX 超时 | ProviderTimeoutError | 是，有次数上限 |
| HTTPX ConnectError | ProviderConnectionError | 是，有次数上限 |
| 非法 JSON、缺少 choices、空正文 | InvalidResponseError | 否 |

其他未显式映射的异常继续向上传播，不承诺当前适配器覆盖所有传输故障。
连接超时与读取超时分别配置；write 使用读取超时，pool 使用连接超时。
注入自定义 HTTP 客户端时，超时由该客户端的配置负责。

默认重试次数为 2，表示最多调用 3 次。默认退避依次为 0.5、1.0 秒，最后一次失败后不再等待。
当前不解析 `Retry-After`，没有 jitter、熔断或端到端 deadline，不应将它描述为完整生产重试系统。

## 动手任务

1. 不看实现，预测以下情况的异常与调用次数：连续 401、连续 429、429 后成功、连续读取超时、首次空正文。
2. 阅读[异常类型](../src/baggage_extractor/providers/errors.py)和[适配器](../src/baggage_extractor/providers/openai_compatible.py)，核对预测。
3. 运行参考测试，查看重试耗尽和重试后成功的断言。
4. 在[HTTP 错误参数化测试](../tests/test_openai_compatible_provider.py)中增加 403 案例：
   应抛出 `AuthenticationError`，HTTP 调用次数为 1，且不修改生产实现。
5. 根据参考退避测试解释如何替换等待函数，为什么测试不应该真的 sleep。
6. 写出一个“不能直接复用模型请求重试策略”的场景，例如创建工单成功但响应丢失，并说明需要幂等或去重。

## 运行与预期

在项目目录执行：

Windows / PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_openai_compatible_provider.py tests\test_config.py
```

macOS / Linux：

```bash
.venv/bin/python -m pytest tests/test_openai_compatible_provider.py tests/test_config.py
```

参考测试与新增 403 案例应通过。预期连续 429、读取超时最多 3 次；429 后成功 2 次；
401、403、非法正文 1 次。`MODEL_MAX_RETRIES=0` 时可重试错误也只请求一次。
测试验证退避调用参数，不实际等待，也不需要真实服务。

<details>
<summary>提示与参考实现</summary>

- `retryable` 表示错误类别允许重试，还必须受剩余次数约束。
- `_generate_with_client` 只捕获领域异常，不用 `except Exception` 吞掉其他错误。
- `@respx.mock` 的 `side_effect` 可模拟先 429、后 200，也可抛出 HTTPX 异常。
- 用 `AsyncMock` 替换 `asyncio.sleep` 后，检查 await 次数和参数；不要仅断言最终成功。
- 重试可能产生额外费用；读取超时并不保证服务端没有执行请求。

</details>

## 常见问题

- 期望 2 次调用却实际 3 次：把“重试次数”误当成了“总尝试次数”。
- 测试变慢：确认测试配置的退避为 0，或在退避专项测试中替换了等待函数。
- 认证错误一直重试：检查是否丢失错误类型或把所有异常统一标为可重试。
- 认为有限重试能保证执行一次：有副作用的业务操作还需要幂等、状态记录与恢复策略。

## 验收与扩展

- [ ] 正确预测错误分类、终止条件和调用次数。
- [ ] 完成 403 变式测试，能说明它与 429 的区别。
- [ ] 理解当前连接/读取超时不等于整个实验的总时间限制。
- [ ] 能解释为什么 HTTP Mock 不能证明某供应商的真实限流行为。

扩展挑战：补充“第一次连接失败、第二次成功”的测试，同时断言请求次数和最终内容。
完成后可继续[第 4 课：领域 Schema](./04-domain-schema.md)。
