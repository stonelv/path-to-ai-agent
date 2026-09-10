# 学习进度

## 当前状态

- 学习阶段：第 1 个月，第 2 天已完成
- 记录时间：2026-09-10
- 月度项目：航司行李额结构化提取程序
- Python 版本：3.13.1

## 已完成

### 开发环境

- 安装并使用 Python 3.13。
- 在项目目录创建 `.venv` 虚拟环境。
- 将项目及开发依赖以 editable 模式安装到虚拟环境。
- 配置环境变量示例文件 `.env.example`。
- 配置仓库级 `.gitignore`，排除虚拟环境、真实 `.env`、缓存、日志和构建产物。

### 项目配置

- 使用 `pyproject.toml` 管理项目元数据、Python 版本和依赖。
- 配置 `src` 布局及 setuptools 包发现。
- 配置 pytest 和 pytest-asyncio。
- 配置 Ruff，并启用基础错误、导入排序、现代化语法和常见缺陷检查。
- 加入 FastAPI、Uvicorn、HTTPX、Pydantic 和配置管理依赖，为后续开发做好准备。

### 最小可运行程序

- 创建 `baggage_extractor` Python 包。
- 设置项目版本为 `0.1.0`。
- 创建命令行入口模块 `baggage_extractor.main`。
- 创建首个包版本单元测试。

### 第 2 天：首次模型调用

- 使用 `pydantic-settings` 从 `.env` 读取模型名称、API Key、Base URL 和超时配置。
- 使用 `SecretStr` 保存 API Key，并保留缺少必要配置时的运行时校验。
- 定义供应商无关的消息、请求、响应和异步 `ModelProvider` 协议。
- 实现基于 HTTPX 的 OpenAI 兼容模型适配器。
- 使用 Pydantic 校验模型服务响应，不把供应商响应对象暴露给业务代码。
- 支持注入异步 HTTP 客户端，为 Mock 测试和连接复用保留边界。
- 记录请求开始时间、结束时间、总延迟、实际模型名称和可选请求 ID。
- 将命令行入口连接到真实模型，完成首次端到端调用。
- 使用 respx 和 Stub Provider 测试配置、请求格式、响应解析与计时逻辑，常规测试不访问真实 API。
- 从国航公开页面及其免费托运行李额附件整理简单、多规则和复杂会员条件三组实验文本。
- 使用三档 Temperature 和最大输出 Token 运行真实模型实验并保存输出、延迟和结论。
- 增加模型空正文校验，避免将 HTTP 200 但无最终回答的响应视为成功。

首次真实调用结果：

```text
Started: 2026-09-09T08:56:14.363494+00:00
Finished: 2026-09-09T08:56:16.922006+00:00
Latency: 2.559 seconds
Model: deepseek-v4-flash
Request ID: not provided
Result: success
```

模型完整提取了航线、舱位、旅客类型、件数、单件重量和三边之和，没有明显补充原文未提供的信息。

### GitHub

- 初始化 Git 仓库。
- 创建首次提交并推送至个人 GitHub 仓库。
- 当前已确认的提交：
  - Commit：`f33be43`
  - Message：`Initialize AI Agent learning project`
  - Time：`2026-09-09 14:15:37 +0800`

## 验证结果

2026-09-09 从仓库根目录使用项目虚拟环境完成最新验证：

```text
Python: 3.13.1
pytest: 10 passed
ruff check: All checks passed
application: real model request succeeded
```

使用的验证命令：

```powershell
.\month-01-llm-foundations\.venv\Scripts\python.exe -m pytest .\month-01-llm-foundations
.\month-01-llm-foundations\.venv\Scripts\python.exe -m ruff check .\month-01-llm-foundations
.\month-01-llm-foundations\.venv\Scripts\python.exe -m baggage_extractor.main
```

## 当前项目结构

```text
path-to-ai-agent/
├── .gitignore
└── month-01-llm-foundations/
    ├── .env.example
    ├── .venv/                  # 仅保存在本地，不提交
    ├── PROGRESS.md
    ├── README.md
    ├── docs/
    │   └── day-02-model-experiments.md
    ├── pyproject.toml
    ├── src/
    │   └── baggage_extractor/
    │       ├── __init__.py
    │       ├── config.py
    │       ├── experiments.py
    │       ├── main.py
    │       ├── telemetry.py
    │       └── providers/
    │           ├── __init__.py
    │           ├── base.py
    │           └── openai_compatible.py
    └── tests/
        ├── __init__.py
        ├── test_config.py
        ├── test_experiments.py
        ├── test_openai_compatible_provider.py
        ├── test_provider_base.py
        ├── test_telemetry.py
        └── test_package.py
```

## 已掌握的知识点

- 虚拟环境用于隔离 Python 解释器和项目依赖。
- `pyproject.toml` 是项目元数据、依赖和开发工具的统一配置入口。
- `src` 布局可以避免测试意外导入仓库根目录中的未安装代码。
- editable install 允许修改源码后立即生效。
- `.env.example` 可以提交变量模板，但 `.env` 和真实 API Key 不能提交。
- 提交前应检查 Git 状态并运行测试与代码检查。
- `Protocol` 可以用结构化类型约束隔离业务代码和具体模型供应商。
- `async`/`await` 适合模型 API 等网络 I/O。
- 外部模型响应属于不可信输入，需要进行结构校验和空结果检查。
- `perf_counter()` 适合计算耗时，UTC 时间适合跨环境记录事件时间。
- 常规单元测试应使用 Stub 或 HTTP Mock，不应消耗真实模型额度。
- 推理模型可能把 `max_tokens` 同时用于内部推理和最终正文，过低上限可能产生空正文。
- HTTP 200 只说明传输成功，应用仍需验证响应结构和正文是否有效。

## 下一步：第 3 天

1. 分别配置连接超时和读取超时。
2. 区分认证失败、限流、超时、服务端错误和无效请求。
3. 只对明确可重试的错误实施有限次数重试。
4. 使用 HTTP Mock 覆盖每种错误，不让自动化测试访问真实模型服务。

## 提交前检查

提交前运行完整测试和 Ruff，并确认 `.env` 未被 Git 跟踪。
