# 规格驱动开发

模型协议回归覆盖明确finish_reason=length/content_filter/tool_calls/function_call及拒答信号；这些响应即使正文为合法动作JSON也不执行。客户端只发一次HTTP请求，接收完成但拒绝的响应携带真实Usage/耗时；TaskRunner记录到普通model_usage并计入预算。缺失用量估算包含已配置输出额度（不等于账单），网络中断仍计model_usage_unknown。旧供应商缺失/null结束字段保留兼容，但不能绕过JSON/参数/能力或目标核验。

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
.venv\Scripts\python -m ruff check --config server/pyproject.toml server scripts tools packaging
node --test server/tests/geometry.test.mjs server/tests/board-status.test.mjs
```

Node 仅用于贡献者测试网页坐标计算和板子状态提示，用户运行服务不依赖 Node。macOS/Linux 使用 `.venv/bin`。静态检查显式使用项目配置，覆盖服务、维护脚本、独立工具和打包入口；android_agent导入分组不依赖运行目录。

Windows便携包构建与真实子进程验收见 [便携包说明](PORTABLE.md)。`server[build]` 固定 PyInstaller6.16.0；产物含实际运行依赖版本、许可、项目与第三方源码及四板固件。构建不发布、不刷设备，ADB由用户从官方单独安装。

网页固件向导的源码入口（先完成四板构建）：

```text
python -m pip install -e "./server[dev,firmware]"
python scripts/collect_firmware.py --output .runtime-local/firmware-catalog
python -m android_agent --firmware-dir .runtime-local/firmware-catalog
python tools/firmware_worker.py diagnose
python -m pytest server/tests/test_firmware.py -q
python server/tests/firmware_demo.py --port 8892
```

catalog 输出目录必须是新目录。缺可选工具/镜像时工作台仍可运行，向导显示安装说明。`--firmware-tool` / `ANDROID_AGENT_FIRMWARE_TOOL` 可以指向兼容协议的独立工具，`ANDROID_AGENT_FIRMWARE_DIR` 设置镜像目录。DEMO 使用临时目录和 memory-backed ROM，不打开真实串口、ADB 或模型；提供正常和断线两个模拟端口，结束时关闭进程。新增测试用真实 manager/worker 配合假 ROM，另用真实子进程验证超时/取消清理。独立工具 `tools/` 使用 GPL-2.0-or-later；应用只通过 JSON 子进程协议交互。便携构建检查主程序没有捆入 esptool、同时记录独立工具全部依赖、许可和对应源码；重建需同时安装 `server[build,firmware]`，从两份 `requirements-installed.txt` 恢复实际版本。

独立工具直接使用esptool API时，必须先在同一ROM连接调用`attach_flash`初始化实际SPI接口，再读取容量与身份。CLI会执行这项准备，直接API不会自动补齐；遗漏会导致真实板容量未知而模拟可能通过。identify仍不加载stub或擦除/编程Flash，不能将旧容量或默认4MB填入未知结果。假ROM测试要求这个前置条件，备份与写入仍在同一连接复核身份。

直接连接还必须设置锁定esptool版本的默认有限串口读取超时（默认3秒），避免命令恢复到无限等待后stub握手挂起；启动失败关闭连接，不自动重试。子进程总期限仍独立生效。假ROM测试覆盖有限超时与stub失败无备份、无Flash写入。

## 持续检查

MCP桥接与真实SDK/stdio协议测试由`./server[dev]`同时安装固定SDK1.30.0；普通用户单独选择`./server[mcp]`，核心`./server`不增加SDK。测试入口：`python -m pytest -q server/tests/test_mcp.py server/tests/test_mcp_api.py`。DEMO和真实Codex配置见 [MCP说明](MCP.md)，真实客户端/手机结果必须与模拟证据分开记录，不能通过自写客户端声称Codex已看见图片。

`.github/workflows/ci.yml` 在push、PR和手动运行时检查OpenSpec正式/归档规格与修改范围，运行Ubuntu/Windows × Python3.10/3.12测试、全部源码Ruff检查、Node22坐标及板子状态测试以及四个固件编译。Actions锁定官方commit，仓库权限只读，不使用手机、开发板、模型密钥或付费服务。

PR相对base SHA检查，push相对before SHA检查，首次push相对空树，手动相对HEAD；非法/缺失SHA立即失败。已归档历史修改不能用旧files.txt通过检查。`esp32dev`构建后执行全部工具测试及实际共享固件g++22场景；其他板型矩阵执行编译。Windows文件symlink测试因权限可能跳过，Linux应实际执行。

```text
python scripts/check_workflows.py
python scripts/ci_base.py --event pull_request --pr-base <已存在的base-sha>
python scripts/check_changes.py --base <base-sha>
python -m unittest discover -s scripts/tests
```

`check_workflows.py`使用dev依赖PyYAML6.0.3检查只读权限、固定Actions、矩阵和产物范围，并拒绝网页测试、静态目录或显式项目配置缺失；注释及其他job不能冒充命令覆盖。完整GitHub语法可用 [actionlint](https://github.com/rhysd/actionlint) 检查两个workflow。源码模式与普通用户运行不需要PyYAML。

`.github/workflows/portable.yml`仅接受workflow_dispatch，在Windows/Python3.12构建四板与便携包，解压到中文/空格路径并运行真实exe smoke；通过后保存ZIP+SHA artifact 7天，不创建GitHub Release。已完成本机等效测试和actionlint1.7.12语法检查，**便携构建工作流尚未远程执行**，不能将配置验证描述为远程打包成功。Windows/Python3.10.21已在独立环境实测通过，3.12.14同步回归；最低安装仅核心依赖的真实启动也通过。Linux工具检查已在禁网Debian13/Python3.12.15容器运行，Git和g++已安装，原生固件测试未skip；原生桌面与未列出的实机组合仍需要对应环境验收，详见 [兼容性证据](COMPATIBILITY.md)。

2026-10-13 公开源码提交 `0097e23` 的 [Continuous validation run 38384089654](https://github.com/shenlan-ai/esp32-android-agent/actions/runs/38384089654) 在公开后第2次运行全部10个job成功：Ubuntu/Windows × Python3.10/3.12各300服务端测试、无skip、1依赖warning，全源码Ruff和CI base测试通过；5网页测试、四板构建、59工具测试（真实共享C++）、正式/归档规格和首次push空树范围检查通过。首次私有状态执行在启动前被账户计费限制拦截，无测试运行；公开后重试成功。此证据只对应该提交，不代表便携workflow已执行或所有设备已验证。

S3 原生 USB 固件矩阵：`python -m platformio run -d hardware/usb_bridge`。它直接复用 BLE 固件的动作调度与验证 headers，原生 g++ 检查继续通过 `python -m unittest discover -s scripts/tests` 执行。USB TCP/CDC 测试不需要设备；网页配网 fixture 为 `python server/tests/usb_demo.py`，仅本机 8892/8893，带 DEMO 标识，结束后关闭服务。详见 [USB说明](USB-SETUP.md)。

Linux最低版本回归另在Debian13.7/Python3.10.22容器完成：231项服务端与57项工具测试均通过、无skip，真实g++共享固件检查、Ruff和工作流检查器通过。独立核心安装（仅`./server`、没有开发工具/esptool/ADB）的真实CLI/HTTP检查也通过，覆盖诊断、工作台资源、缺ADB错误及正常关闭。构建时下载公开依赖，检查容器使用`--rm --network none`且不接设备、个人配置或模型；版本、源码快照SHA及原始命令见`verify-linux310-regression`归档。这是Debian容器证据，远程Ubuntu runner和原生桌面仍待验证。

最短入口见 [English（默认）](../README.md) / [简体中文](../README.zh-CN.md)，起始条件明确的任务见 [示例](EXAMPLES.md)。真实手机与模型验收使用 [结果模板](ACCEPTANCE.md)；按实际控制模式、机型/Android/API、固件/代码/模型版本和起始条件记录，不能以软件测试证明全机型兼容。

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
