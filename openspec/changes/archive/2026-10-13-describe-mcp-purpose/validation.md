# Validation

2026-10-13，纯文档修正。

- 功能变更归档后，`openspec validate --all --strict --no-interactive`实际返回16通过/1失败；原因是新正式MCP规格的Purpose仍为OpenSpec自动生成TBD占位句。归档过程成功且37个归档规格校验通过，不改写该历史证据。
- `openspec validate describe-mcp-purpose --strict --no-interactive`实现前通过（skip_specs信息提示，无行为delta）。
- 替换Purpose后，`openspec validate --all --strict --no-interactive`：17正式规格+本变更，共18通过/0失败。
- `openspec validate --archived --no-interactive`：37通过/0失败。
- Python逐字比较新正式规格的Requirements与已归档add-mcp-device-tools的ADDED Requirements：四项需求及全部场景完全一致，仅Purpose变化。
- `.venv/Scripts/python scripts/check_changes.py`通过；`git -c core.safecrlf=false diff --check`通过。

未重复服务端/硬件测试：本变更不修改任何运行代码或行为；先前Python3.10/3.12各347 passed、1权限skip、1依赖warning，48 MCP测试和真实Codex/手机验收证据均保留。MCP入口`android-agent-mcp --help`实际通过，最终工作台仍在线、BLE/HID ready、task idle；新8903 fixture已通过其拥有的PTY正常Ctrl-C关闭（Uvicorn记录shutdown complete），被自动审批拒绝停止的旧8901仍保留，未绕过重试。

完成后执行`openspec archive describe-mcp-purpose --yes`及最终全规格、归档、范围和空白检查；完成命令输出保留最终结果。
