# Validation

日期：2026-10-13；Windows、Python3.12.14/3.10.21、MCP SDK1.30.0、Codex CLI0.154.0及桌面新会话。

## 软件检查

- 实现前阅读AGENTS、正式MCP/Agent规格，`openspec list --specs`有18个规格，`openspec list`无活动变更。
- `openspec validate complete-mcp-action-discovery --strict --no-interactive`：实现前及schema兼容性设计更新后通过。
- `.venv/Scripts/python -m pytest -q server/tests/test_mcp.py server/tests/test_mcp_api.py`：70 passed、1依赖warning；覆盖12动作集合一致性、10种ADB输入逐动作SDK→HTTP→真实控制器、BLE/USB两种持续绘图映射、能力就绪/校准/断线/维护过滤、整数schema与字符串/浮点/布尔/越界/3项坐标拒绝。已有停止、竞争和画面期限测试保持通过。
- `.venv/Scripts/python -m pytest -q server/tests`：最终369 passed、1 Windows symlink权限skip、1 Starlette依赖warning，37.82s。
- `.runtime-local/python310/venv/Scripts/python -m pytest -q server/tests`：最终369 passed、1相同skip、1依赖warning，38.44s。
- `.venv/Scripts/python -m ruff check --config server/pyproject.toml server scripts tools packaging`：通过。
- `openspec validate --all --strict --no-interactive`：18正式规格+活动变更，共19项通过。
- `.venv/Scripts/python scripts/check_changes.py`及`git -c core.safecrlf=false diff --check`：通过；结束前再检查归档路径。

## 接入与实机

- 本机API状态确认手机在线、BLE就绪且path/circle可用，先共享stop得到hid_release_sent，再关闭旧控制器重启源码工作台，恢复COM5 BLE与已保存校准。没有刷固件或修改模型设置。
- 忽略的项目级`.codex/config.toml`注册源码Python stdio；`codex mcp get android_agent --json`只打印安全字段，确认源码绝对路径与loopback8890。全局配置保持原样。实机结束已移除android_action临时预批准，仅保留源码注册。
- 新建桌面Codex会话`01a13550-f70c-7c02-a0f2-159f36aed08c`，任务名称“通过源码 MCP 在安卓笔记中画笑脸”；已完成62次原生MCP调用，在小米笔记新建图片笔记，通过3次circle和一次9点path绘制笑脸，保存、返回列表并重新打开核验图案仍存在。最后stop返回hid_release_sent/firmware_in_progress=false，未用shell/ADB替代手机输入。模型发生一次现有笔记列表误定位，没有编辑，返回并打开正确条目；一次保存过期被拒绝，重新观察后保存。完整证据见docs/acceptance/2026-10-13-codex-mcp-notes-smiley.md。
- `.venv/Scripts/python .runtime-local/mcp-notes-observe.py`：新的源码stdio SDK客户端确认公开schema为标准整数items，并独立获取实际手机最终笔记图像；主会话view_image确认笑脸轮廓、双眼与连续U形笑嘴。原图/裁剪仅保存忽略目录。
- 初始桌面会话初始化早于schema显示修复，但仍成功发送严格整数path；`.venv/Scripts/python .runtime-local/mcp-notes-verify.py`启动新的真实Codex CLI0.154.0只读会话，仅调用一次status和一次screenshot，退出0，确认实际笑脸、points嵌套数值数组和全部12种声明；未执行android_action。两次上游模型流断开/重连后完成，保留原始JSONL；这不是桥接自动重放或审批审查拒绝。该单张图仅作独立视觉/schema验证，退出并重开的保存链路由桌面会话验证。
- 修改的4份用户文档检查66个本地Markdown目标均存在，中文/英文入口保持。
- 本机Codex项目配置确认没有approval_mode字段，源码注册仍存在；临时动作预批准移除。

## 完成与归档

所有实现及实机尝试、恢复和结果已记录。归档前再次执行`openspec validate --all --strict --no-interactive`（18正式规格+本变更19通过）、`openspec validate --archived --no-interactive`（40通过）、`python scripts/check_changes.py`（18修改文件覆盖）及空白检查，均通过。随后执行`openspec archive complete-mcp-action-discovery --yes`同步正式规格，并再次检查正式/归档规格及范围；实际命令结果在完成工具输出及最终答复中保留，不提前声称归档后的检查通过。

## 限制与未执行

未编译/刷写固件、未重建便携包、未进行远程CI或推送。本次没有固件/前端修改，无需对应编译或网页回归。Windows symlink测试权限skip明确保留；Linux和其他系统/手机/板型未新增实机证据。原始手机图像和会话记录留在忽略目录，不提交私人笔记。
