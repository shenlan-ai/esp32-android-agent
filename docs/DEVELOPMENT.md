# 规格驱动开发

已验证工具：OpenSpec 1.13.1。Windows 下若 PowerShell 限制 npm 脚本，使用 `openspec.cmd`。项目文件使用 UTF-8。

2026-10-12本机验证环境：Python3.12.14、Node24.21.0。`implement-verified-agent`旧归档验证记录中的“Node25”为版本笔误；实际测试在Node24.21.0执行。更正证据见`correct-agent-validation-environment`，测试计数与结果保持原记录。普通用户运行服务不需要Node。

## 开始变更

```text
openspec list --specs
openspec list
openspec new change <change-id>
openspec instructions proposal --change <change-id> --json
```

读取相关正式规格；按照指引依次完成 proposal.md、specs、design.md、tasks.md。需求和场景保留英文结构标题和 SHALL/MUST，内容使用中文。

变更中维护 files.txt，每行一个仓库相对路径或有限目录通配符，例如 `server/android_agent/adb.py`。OpenSpec 自身文件归属其变更，正式规格生成路径也应列入范围。禁止 `*`、`**` 或 `**/*` 覆盖全仓库。

不改变产品行为时在 `.openspec.yaml` 写 `skip_specs: true`，明确为什么无需 delta；仍填写设计、任务、文件范围和验证记录。

## 实现与检查

```text
openspec validate <change-id> --strict --no-interactive
python scripts/check_changes.py
python -m unittest discover -s scripts/tests
```

实现前规格校验，修改范围扩展先更新 artifacts。新增功能需要适合该行为的测试。完成任务后更新 checkbox，在 validation.md 记录证据。

范围检查默认比较 HEAD 与工作树，并包含未跟踪文件。首次提交前检查所有项目文件。CI 使用 `python scripts/check_changes.py --base <base-sha>`，包含基线之后所有修改；旧归档清单不能为新修改提供范围。

## 完成变更

服务端检查（在仓库根目录，已安装 `./server[dev]`）：

```text
.venv\Scripts\python -m pytest -q server/tests
.venv\Scripts\ruff check server
node --test server/tests/geometry.test.mjs
```

Node 仅用于贡献者测试网页坐标计算，用户运行服务不依赖 Node。macOS/Linux 使用 `.venv/bin`。

自动任务关键测试使用MockTransport、假手机/控制器/模型，不调用付费接口。离线浏览器验收可执行：

```text
.venv/Scripts/python server/tests/agent_demo.py
```

打开`http://127.0.0.1:8892`。页面明确标注DEMO，不开放真实开发板端口，不调用真实ADB或外部模型；支持正常任务、慢请求暂停、模型测试和本机记录导出。模拟数据只进入`.runtime-local/agent-demo`。结束后关闭此进程，不能把其成功画面作为实机验收。

```text
openspec archive <change-id> --yes
openspec validate --all --strict --no-interactive
openspec validate --archived --no-interactive
python scripts/check_changes.py
```

归档前全部任务完成且 validation.md 存在；未完成任务不能勾选或归档。归档更新正式规格，自动生成的规格仍是该变更的一部分。

首次规范变更同时纳入之前已经讨论并写出的架构文档。后续代码与说明必须先有新变更。Git 提交信息包含变更 ID，不自动发布远程版本。
