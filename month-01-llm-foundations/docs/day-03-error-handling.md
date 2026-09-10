# Day 3 异步与错误处理

> 作者的实现记录。包含练习、预期结果与验收命令的公共教程见[第 3 课](../lessons/03-error-handling.md)。

## 学习目标

- 将连接超时和读取超时分别配置。
- 将供应商错误转换为业务可识别的异常类型。
- 只对限流、服务端错误、连接失败和超时进行有限次数重试。
- 使用 HTTP Mock 验证成功、失败和重试路径。

## 实现结果

`OpenAICompatibleProvider` 现在支持：

- `MODEL_CONNECT_TIMEOUT_SECONDS` 和 `MODEL_READ_TIMEOUT_SECONDS`；
- 认证失败、无效请求、限流、服务端错误、超时、连接失败和无效响应分类；
- 最多 `MODEL_MAX_RETRIES` 次指数退避重试；
- 不重试认证失败、无效请求和无效模型响应。

测试不访问真实模型服务，并验证了 HTTP 状态码分类、重试次数和重试后成功。
