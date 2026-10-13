2026-10-13，变更先strict校验后实施；发现根目录静态规则不一致时先更新design/files/spec再校验及修改配置。

## Windows检查
- Python3.10.21与3.12.14：`python -m unittest discover -s scripts/tests -q`各57项通过，无skip；新增6项真实YAML变异测试覆盖完整配置、缺网页测试、注释冒充、错误job、缺tools、缺项目配置。
- 两环境：`python -m ruff check --config server/pyproject.toml server scripts tools packaging`通过；`python scripts/check_workflows.py`通过。
- Node24.21.0：`node --test server/tests/geometry.test.mjs server/tests/board-status.test.mjs`，5项通过。
- actionlint1.7.12：检查ci.yml与portable.yml，无错误。

## Linux实际执行
隔离镜像基于官方python:3.12-slim，Debian13.7/Python3.12.15，g++14.2.0，Git2.47.3。镜像ID：`sha256:e7355313e93d987e861b06e506ced7cf99e3c582411b2ed8d410da1d99b1ab65`。运行使用`docker run --rm --network none`，不挂设备、Docker socket或主机个人配置；只使用公开源码快照、固定ArduinoJson及依赖。Ruff检查额外挂只读的最新项目pyproject.toml，声明android_agent为first-party。构建联网安装公开依赖，正式检查禁网。

- `python -m pytest -q server/tests`：231 passed，0 skipped，1条Starlette/httpx弃用警告；文件链接场景实际执行。
- `python -m unittest discover -s scripts/tests -q`：57项通过，无skip，包含真实g++调度/诊断运行和临时Git仓库测试。
- `python -m ruff check --config server/pyproject.toml server scripts tools packaging`和`python scripts/check_workflows.py`通过。
- 官方node:24.21.0-alpine，禁网、只读源码：同两组Node测试，5项通过，无skip。
- 原始环境、依赖与检查日志保存在ignored `.runtime-local/linux-diagnostic-*.log`，未提交配置、Flash、设备身份或截图。

首次工具检查因镜像缺Git失败11项、跳过1项；补装Git后完整重跑全部通过。首次根目录Ruff继承外部默认规则；显式配置后仍出现first-party推断不一致，声明项目包后两平台通过，未批量改无关源码。失败未计为通过。

## 规格与限制
`openspec validate cover-diagnostics-in-ci --strict --no-interactive`、全部正式/活动及归档校验、`python scripts/check_changes.py`与`git diff --check`均通过；归档后再次校验。

没有Git remote，未执行GitHub远程CI。Debian容器不等于Ubuntu runner、Linux原生桌面或macOS；Linux/Python3.10未运行。本变更未修改产品行为或再次构建便携包，上一开发包的来源快照不包含本次CI/config修改。未进行刷写、手机动作或模型调用。

生产只读状态仍是BLE0.1.1/connected=true/hid_ready=false，完整备份此前失败；等待用户更换可靠数据线及直连USB后继续，实机变更保持活动，不能以容器通过声明手机或目标全机型通过。
