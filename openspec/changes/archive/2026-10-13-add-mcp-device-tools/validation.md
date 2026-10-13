# Validation

日期：2026-10-13。执行环境Windows/Python3.12.14和3.10.21；mcp SDK1.30.0；真实Codex CLI0.154.0。

## 执行命令与结果

- `openspec list --specs` / `openspec list`：实现前16个正式规格、无活动变更，相关治理/设备/截图/手动/执行规格已读取。
- `openspec validate add-mcp-device-tools --strict --no-interactive`：实现前与设计范围完善后均通过。
- `.venv/Scripts/python -m pytest -q server/tests/test_mcp.py server/tests/test_mcp_api.py`：最终48 passed，1依赖弃用warning。
- `.venv/Scripts/python -m pytest -q server/tests`：最终347 passed、1 Windows symlink权限skip、1依赖弃用warning，39.12s。
- `.runtime-local/python310/venv/Scripts/python -m pytest -q server/tests`：最终347 passed、1相同skip、1 Starlette依赖弃用warning，40.08s。先用主环境`python -m pip --python <310-python> install -e './server[dev,mcp]'`安装可选SDK（310环境无pip模块，未假装安装成功）。
- `.venv/Scripts/python -m ruff check --config server/pyproject.toml server scripts tools packaging`：通过，含新增fixture焦点提示。
- `.venv/Scripts/python -m unittest discover -s scripts/tests`：59 passed，含实际共享固件C++测试，无Flash写入。
- `node --test server/tests/geometry.test.mjs server/tests/board-status.test.mjs`：5 passed。
- `.venv/Scripts/python scripts/check_workflows.py`：通过；dev extra安装SDK使现有CI矩阵自动涵盖新增协议测试，未修改工作流。
- `openspec validate --all --strict --no-interactive`：归档前16正式规格+本变更，共17项通过。
- `openspec validate --archived --no-interactive`：归档前36项通过。
- `.venv/Scripts/python scripts/check_changes.py`：通过，所有实现/文档/测试及本次元数据由files.txt覆盖。
- `git -c core.safecrlf=false diff --check`：通过。
- 独立核心环境：`python -m venv --without-pip .runtime-local/mcp-core-env` + `python -m pip --python <core-python> install -e ./server`，真实安装通过；`.venv/Scripts/python .runtime-local/mcp-core-smoke.py`确认未安装SDK、核心导入与真实CLI/HTTP首页/会话正常；MCP入口缺SDK时stderr简明、stdout为空。

## 实际Codex与手机

通过单次CLI配置覆盖启动stdio桥接，`codex exec --ephemeral --json -s read-only`仅调用android_agent MCP。全部原始JSONL/事件/图片位于被忽略的`.runtime-local/mcp-*`，不提交秘密或原始手机数据。没有将自写SDK客户端测试等同Codex验收。

- `.venv/Scripts/python .runtime-local/mcp-codex-acceptance.py demo`：真实Codex看图→tap成功→旧凭据重复拒绝→type mcp_hello→新图核验→stop，通过。首次structuredContent使图片未交付到模型的问题已修正；审批策略默认拒绝输入的配置问题改为仅本次已授权动作明确预批准，全局配置保持。
- `.venv/Scripts/python .runtime-local/mcp-codex-acceptance.py phone`：真实Redmi Note14/Android15/经典ESP32 BLE0.1.4；按钮tap正确、重复凭据stale_observation、stop hid_release_sent。输入框被模型误定位，type完成但文本为空，停止且不重放，记录为部分通过。
- `.venv/Scripts/python .runtime-local/mcp-codex-acceptance.py phone-focus`：独立8903本机测试页显示焦点；中心位置提示后Codex取图、tap(500,670)、新图确认FOCUS OK、只type一次、再取图确认字段和结果行均为mcp_hello、stop hid_release_sent，通过。页面事件独立确认focus、9次逐字符input及准确最终文字、1个配对pointerdown/up。
- 机型/板型/校准、首轮失败和第二轮辅助条件见`docs/acceptance/2026-10-13-codex-mcp.md`。当前工作台仍在8890运行BLE，任务idle且输入已释放。

## 限制、未执行与审批拒绝

新MCP没有新增Android16/17、其他品牌、S3 USB或实物拔线的证据；模拟取消/断线、SDK协议与编译不能代替这些实机情况。外部模型仍可能定位错误；首次失败及第二次有提示条件明确记录，不声明任意任务自动可靠成功。ASCII/手动英文输入法边界保持。

未刷写/重编固件、未构建新便携exe、未推送本变更/执行远程CI。便携工作台使用独立Python MCP桥接。未修改用户全局Codex配置。强制杀进程不保证停止清理。

自动审批审查拒绝停止旧8901测试服务，返回“blocked by policy”，没有更具体说明；没有重试该动作，保留旧进程并在新8903端口完成焦点验收。此前8894服务同样未触碰。拒绝只影响测试服务清理，不是手机控制或功能验收失败。

全部实现与验收任务已完成；随后按规范执行`openspec archive add-mcp-device-tools --yes`、正式/归档规格和范围/空白检查（结果由完成变更的命令输出保留）。
