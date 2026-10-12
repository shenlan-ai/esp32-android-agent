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

Windows便携包构建与真实子进程验收见 [便携包说明](PORTABLE.md)。`server[build]` 固定 PyInstaller6.16.0；产物含实际运行依赖版本、许可、项目与第三方源码及四板固件。构建不发布、不刷设备，ADB由用户从官方单独安装。

## 持续检查

`.github/workflows/ci.yml` 在push、PR和手动运行时检查OpenSpec正式/归档规格与修改范围，运行Ubuntu/Windows × Python3.10/3.12测试、Node22坐标测试以及四个固件编译。Actions锁定官方commit，仓库权限只读，不使用手机、开发板、模型密钥或付费服务。

PR相对base SHA检查，push相对before SHA检查，首次push相对空树，手动相对HEAD；非法/缺失SHA立即失败。已归档历史修改不能用旧files.txt通过检查。`esp32dev`构建后执行全部工具测试及实际共享固件g++22场景；其他板型矩阵执行编译。Windows文件symlink测试因权限可能跳过，Linux应实际执行。

```text
python scripts/check_workflows.py
python scripts/ci_base.py --event pull_request --pr-base <已存在的base-sha>
python scripts/check_changes.py --base <base-sha>
python -m unittest discover -s scripts/tests
```

`check_workflows.py`使用dev依赖PyYAML6.0.3检查只读权限、固定Actions、矩阵和产物范围；完整GitHub语法可用 [actionlint](https://github.com/rhysd/actionlint) 检查两个workflow。源码模式与普通用户运行不需要PyYAML。

`.github/workflows/portable.yml`仅接受workflow_dispatch，在Windows/Python3.12构建四板与便携包，解压到中文/空格路径并运行真实exe smoke；通过后保存ZIP+SHA artifact 7天，不创建GitHub Release。当前已完成本机等效测试和actionlint1.7.12语法检查，**尚未执行GitHub远程CI**，不能将配置验证描述为远程运行成功。远程Linux/最低Python矩阵和实机任务分别需要对应环境验收。

S3 原生 USB 固件矩阵：`python -m platformio run -d hardware/usb_bridge`。它直接复用 BLE 固件的动作调度与验证 headers，原生 g++ 检查继续通过 `python -m unittest discover -s scripts/tests` 执行。USB TCP/CDC 测试不需要设备；网页配网 fixture 为 `python server/tests/usb_demo.py`，仅本机 8892/8893，带 DEMO 标识，结束后关闭服务。详见 [USB说明](USB-SETUP.md)。

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
