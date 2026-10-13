# 验证记录（2026-10-13）

## 环境与完整性

- 实现/测试前：`openspec validate verify-linux310-regression --strict --no-interactive`通过，skip_specs为true，仅增加文档证据。
- 使用`source_archive`生成当前已跟踪工作树快照；未包含参考检出或私人运行目录。源码ZIP SHA256：`e19a9773cfb360b352454789783f11ac6314cf7b0dbbd0a72d1600424e0e18a9`。六个关键文件与当前树逐字节核对一致；额外复制当前固定ArduinoJson/src供真实C++检查。
- 官方`python:3.10-slim`实际环境：Python3.10.22，Debian13.7，g++14.2.0，Git2.47.3。验证镜像安装`./server[dev,firmware]`，核心镜像仅安装`./server`；实际依赖freeze分别保存ignored日志，没有将浮动标签作为版本证据。
- `docker build --target validation --tag esp32-android-agent-linux310-validation:20261013 .runtime-local/linux310-validation-20261013`退出0；image ID：`sha256:ac5027b798a56ba9a88e34ba6efa8281a491d04f8a1f66840067e1bb81a1e165`。
- 同context的`docker build --target core --tag esp32-android-agent-linux310-core:20261013 ...`退出0；image ID：`sha256:cb5445807796603661be8e3c1fd73332da019c9ee0f63fdbc3504f8eeba3c79f`。

## 实际执行

以下各命令在`docker run --rm --network none esp32-android-agent-linux310-validation:20261013`中执行，镜像ENTRYPOINT为python；各退出0，无设备/个人配置/Docker socket挂载，无付费模型请求。

- `-m pytest -q server/tests`：231 passed、零skip、24.70秒，1条Starlette/httpx弃用警告。
- `-m unittest discover -s scripts/tests -q`：57 tests、3.068秒、OK、零skip；真实g++编译并运行27项调度与7项诊断场景。日志中的flash_board参数拒绝是预期负向测试，没有打开真实串口或刷写。
- `-m ruff check --config server/pyproject.toml server scripts tools packaging`：All checks passed。
- `scripts/check_workflows.py`：Workflow invariants passed。
- 环境/依赖：`--entrypoint sh ... -c 'python --version; cat /etc/os-release; g++ --version; git --version; python -m pip freeze'`，完整版本记录在`.runtime-local/linux310-environment.log`。

核心镜像使用相同`--rm --network none`，只读挂载无敏感信息的`.runtime-local/linux310-core-smoke.py`至`/tmp/core-smoke.py`，不映射主机端口。运行`python /tmp/core-smoke.py`退出0：确认pytest/ruff/esptool均未安装；真实`python -m android_agent --diagnose`及`--no-browser --port <临时端口> --data-dir <容器临时目录>`启动；工作台、app.js、board-status.js、i18n.js均200；状态报告adb_available=false、tool_available=false、agent=idle；devices返回409且明确ADB原因。发送terminate后10秒内完成应用shutdown并回收子进程（POSIX返回码-15，无kill超时）。

## 日志与限制

镜像context/快照在`.runtime-local/linux310-validation-20261013/`；原始构建、server/tools/static/workflows、环境、核心依赖及smoke日志为`.runtime-local/linux310-*.log`，均ignored。本次不重复已通过的Node检查或四板编译，不修改产品代码和依赖。通过不等于Linux原生桌面、Ubuntu远程CI、macOS、真实手机/BLE或模型任务验收。硬件完整备份与hid_ready仍未通过，相关变更保持活动状态。

归档前检查：`openspec validate --all --strict --no-interactive` 19 passed；`openspec validate --archived --no-interactive` 20 passed；`python scripts/check_changes.py`覆盖100项修改通过；`git diff --check`退出0（仅既有LF/CRLF提示，无空白错误）。全部任务完成后使用标准archive命令归档，并再次执行正式/归档/范围检查。
