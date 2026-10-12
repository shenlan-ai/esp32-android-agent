# Validation

2026-10-12，Windows、Python3.12.14、Node25。此变更完成自动任务软件闭环，不代表完整项目已发布或手机/模型实机验收完成。

## 自动检查

- `.venv/Scripts/python.exe -m pytest -q server/tests`：92 passed、1 skipped、1 warning。跳过项为真实文件符号链接测试，本机Windows无创建权限；普通目录越界与非法任务ID拒绝已实际通过。Starlette/anyio弃用警告，无测试失败。
- `.venv/Scripts/ruff.exe check server`：通过。
- `.venv/Scripts/python.exe -m unittest discover -s scripts/tests`：19 passed，无跳过；包括真实固件调度/验证头文件的g++编译与22场景运行，固件源码本变更未修改。
- `node --test server/tests/geometry.test.mjs`：3 passed；`node --check`检查app.js与tasks.js通过。
- OpenSpec变更严格校验和`python scripts/check_changes.py`通过；归档后再次检查全部规格与归档。

## 关键验证覆盖

- MockTransport核对API前缀、Base64图、鉴权头、额外参数、usage/估算、max_completion_tokens互斥处理。HTTP错误、超时、过大/非法响应不得暴露凭据或自动重试。
- 严格JSON拒绝重复键、NaN、对象外正文、布尔坐标、越界坐标、额外动作字段、主机frame_id和未声明能力/按键。
- 单步执行后独立前后画面核验；actor假done不能直接成功；最终核验使用独立调用与最新画面。目标区域、方向和画面年龄变化时旧动作不发送。
- 模型请求取消后可手动输入、恢复重新规划；拖动中暂停记录结果未知并释放UP，停止不死锁。设备错误暂停且不重放，黑屏在调用模型前暂停。
- 动作限制、Token恢复拒绝、真实外层超时取消、暂停时间排除、步骤图最多12张；默认不落截图，启用后保存；清空当前视图保留磁盘历史。
- SSE队列溢出重置、订阅移除、初始reset与changed事件。导出只含任务文件，拒绝路径越界/非法ID；真实符号链接拒绝尚需权限允许的主机或CI复核。
- HTTP任务、历史、图片、ZIP、模型测试与停止集成验证；并发模型测试/任务启动被拒绝，停止取消探测并关闭客户端。

## 浏览器验收

- 离线fixture8892使用假ADB和HTTP MockTransport，不开放物理串口，不调用外部模型。页面醒目标注DEMO，模型输出由模拟场景提供，不能作为实际视觉判断准确率证据。
- 正常任务显示规划、单步说明、预期、核验证据、执行前后图与最终目标成功；运行中手动输入按钮禁用。
- 慢请求中暂停，手动Home成功，继续重新规划；刷新后恢复任务状态、步骤与目标文本。修复了刷新后目标输入框未回填的问题。
- 中英切换正常；查看历史、清空当前视图后历史仍保留。
- 网页下载ZIP包含before/after图片、events.jsonl、summary.json；ZipFile.testzip()返回None。本机验收包移动到忽略目录`.runtime-local/agent-demo/browser-export.zip`。
- 可选参数temperature/max_completion_tokens保存后刷新恢复，模型测试和完整任务继续通过。模型测试使用合成图；处理中测试/开始任务按钮同时禁用，Esc取消并返回no_held_input。修复轮询过早启用与首次点击未同步锁定开始按钮的问题。
- 最新截图`.runtime-local/agent-completed-demo.png`，摘要预览`.runtime-local/agent-completed-preview.png`；模拟页面与服务已关闭。
- 真实8890服务已用最新代码启动并保留页面；无手机、无模型配置时入口正确禁用，COM5仍被发现，真实与模拟页面JS错误日志为空。

## 尚未执行的验收

当前没有ADB手机或真实视觉模型配置，因此没有实际供应商请求、手机视觉任务成功率、BLE手机输入精度或Android15–17多厂商记录。当前板先前已刷入且12项真实串口检查通过，不能扩大为手机HID验收。

S3/S2原生USB固件、Windows发布包/启动器、CI与真实手机/板子发布验收仍属整体项目后续工作，不由此变更宣称完成。
