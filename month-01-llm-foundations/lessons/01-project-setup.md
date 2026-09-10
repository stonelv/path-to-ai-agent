# 第 1 课：工程初始化与配置

[课程索引](./README.md) · 下一课：[模型调用](./02-model-calls.md)

## 目标与前置

建议 1～2 小时。需要会编辑 Python 文件、使用终端和 Git。
本课完成后，你应能解释“用哪个 Python 安装、运行和测试”，并证明缺少配置时不会静默使用默认凭据。

## 工程问题

同一条命令在不同机器上可能使用不同解释器和依赖。先解决可运行性，再调用模型。
当前项目使用 `src` 布局、editable install、pytest 和 Ruff；配置通过 Pydantic Settings 读取。

## 动手任务

1. 按[环境指南](../../docs/setup.md)创建虚拟环境并安装项目，不需要创建 `.env`。
2. 阅读[项目配置](../pyproject.toml)，找出 Python 要求、开发依赖、测试目录和 Ruff 规则。
3. 运行下面的参考测试，解释为何不需要真实 API Key。
4. 在自己的工作副本中为[配置测试](../tests/test_config.py)增加变式：
   用 `monkeypatch.delenv(..., raising=False)` 删除 `MODEL_API_KEY`、`MODEL_NAME`、`MODEL_BASE_URL`，
   调用 `Settings(_env_file=None)`，断言抛出 `ValidationError`，且错误中包含三个缺失字段。
   不要删除磁盘上的 `.env` 或修改机器的永久环境变量。
5. 保存运行结果，并说明虚拟环境、项目安装和运行时配置各自解决什么问题。

## 运行与预期

在项目目录执行。依赖安装方式见环境指南。

Windows / PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_package.py tests\test_config.py
```

macOS / Linux：

```bash
.venv/bin/python -m pytest tests/test_package.py tests/test_config.py
```

参考测试应通过。新增测试也应通过，并确实检查缺少必填配置，而不是仅捕获任意异常。
本课不启动真实模型程序。

<details>
<summary>提示与参考实现</summary>

- [Settings](../src/baggage_extractor/config.py) 中没有给三个模型连接字段设默认值。
- `_env_file=None` 禁止读取文件，但不会屏蔽系统环境变量，所以测试还要用 monkeypatch 临时移除它们。
- 已有测试演示了环境变量注入和非法超时；新增测试应验证不同的失败场景。
- 用 `ValidationError.errors()` 中的 `loc` 与 `type` 检查对应字段的 `missing` 错误，避免匹配易变的完整报错文本。
- `monkeypatch` 会在测试后恢复环境；测试不应写入用户配置。

</details>

## 常见问题

- 找不到模块：检查是否使用同一个虚拟环境完成 editable install 和测试。
- 新测试没有报错：可能仍从环境变量或 `.env` 读到了配置。
- 只检查抛出异常：可能把非法超时等其他错误误当成缺少配置；应检查对应错误字段。

## 验收与复盘

- [ ] 包与配置测试通过，新增缺少配置测试通过。
- [ ] 能解释为什么不使用全局 pip，也不用为了激活环境修改执行策略。
- [ ] 能解释 `.env.example` 可以提交，真实 `.env` 不可以提交。
- [ ] 能说明 editable install 与“复制一份源码到环境中”的差异。

扩展挑战：补充连接超时等于 0 时的测试，不改变生产配置的既有校验规则。
