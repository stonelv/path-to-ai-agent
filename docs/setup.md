# 环境准备

[返回课表](../README.md)

需要会基本编程、Git、HTTP、JSON 和测试。不熟悉 Python 时按需查阅
[类型与基础语法](https://docs.python.org/3.13/tutorial/)、
[asyncio](https://docs.python.org/3.13/library/asyncio.html)和
[pytest](https://docs.pytest.org/en/stable/getting-started.html)，不用先完成一整套补课。

## 安装一个项目

教学基线为 Python 3.13。两个项目使用各自的虚拟环境，不依赖彼此的源码或安装状态。
以下以项目一为例；学习导学或第 05～06 课时，把工作目录换成 `projects/tool-agent`。

Windows / PowerShell，从仓库根目录执行：

```powershell
Set-Location .\projects\baggage-extractor
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

macOS / Linux：

```bash
cd projects/baggage-extractor
python3.13 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

已有环境无需重建。没有 `py` 时，确认 `python --version` 为 3.13 后使用
`python -m venv .venv`。不需要激活环境，也不要修改系统执行策略或全局安装依赖。
目录迁移后重新创建虚拟环境和 editable 安装，不直接搬用旧环境；保留自己的配置与实验结果。

## 安装成功的标准

- pytest 退出码为 0，Ruff 无错误；测试数量不是验收标准。
- 不需要 `.env`、API Key 或模型账户，测试不执行付费调用。
- 刻意未完成的练习不在普通测试范围内；各课给出单独运行方法和初始失败预期。
- 命令执行不调用模型不等于安装无需网络。依赖采用版本范围，复现问题时记录实际版本。

课程命令以所在项目目录为工作目录。Windows 命令使用虚拟环境中的 Python；
macOS/Linux 对应 `.venv/bin/python`，文件路径使用 `/`。本次维护验证平台为 Windows，
其他平台命令不代表已经实机验证。

## 运行与费用

- [提取器](../projects/baggage-extractor/README.md)：离线评分、可选真实模型、API 与容器命令。
- [工具 Agent](../projects/tool-agent/README.md)：脚本化离线演示，没有真实模型接入，不需要密钥。

真实调用前确认数据可外发、请求数量和费用边界。不得提交凭据、公司资料或个人信息；
模型效果、实际费用和部署未验证时明确记录，不用 Stub 成功替代。

## 常见问题

| 问题 | 排查 |
| --- | --- |
| 找不到项目包 | 核对当前项目目录，使用该项目虚拟环境并重新执行 editable 安装 |
| 编辑器与终端结果不同 | 将编辑器解释器切换为对应项目的 `.venv` |
| 普通测试要求真实密钥 | 检查是否误运行真实 CLI；不要通过填入私人密钥修复离线测试 |
| 初始练习抛出 `NotImplementedError` | 这是待实现起点；按本课说明实现，不删除测试 |
| 真实模型拒绝参数或结构化输出 | 按项目说明核对服务能力，不能把兼容 API 当作兼容所有能力 |
