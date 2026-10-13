## 实现与验证

实现前`openspec validate report-firmware-failure-stages --strict --no-interactive`通过。

- Python3.12.14、Python3.10.21：`python -m unittest discover -s scripts/tests -q`各51 passed；真实perform后续段失败、真实main失败信封及脱敏、stub失败和写后校验阶段、无重试/无完成文件均覆盖。第一次工具测试因MAC列表索引误选Flash容量而失败，修正索引后两环境通过；实现没有泄漏该模拟MAC。
- 两Python版本：在server目录`python -m pytest -q tests/test_firmware.py`各42 passed。新增真实子进程覆盖有效/旧/伪造/布尔/未知枚举/越界计数/非法JSON/超长输出/退出码不一致，错误只显示主机自有文本；计数文件证明只启动一次。备份/写入超时分别提示未写或结果未知并回收进程；写后校验失败不假称未写Flash。
- 在server目录Ruff检查相关主机、工具与测试文件通过。未修改固件或新增依赖，不重新编译固件；未重建旧便携包，不能声称旧dist包含新提示。

## 本机生产边界与限制

服务确认agent=idle、firmware busy=false后优雅重启，加载新主机提示和容量期限；新服务exec session15897，日志保留本机ignored路径。恢复原手机选择与BLE/COM5，真实画面可取得，板上串口connected=true、firmware0.1.1、hid_ready=false。

独立生产FirmwareTool以明确错误的预期身份运行只读backup入口，真实ROM读取身份后拒绝，真实worker与主机边界得到固定“board identification / no Flash was written”提示，无身份回显、无完成文件、无Flash写入；随后恢复生产BLE绑定。此项是刻意构造的身份拒绝验收，不是实际传输失败根因、完整备份成功或BLE手机输入通过。

为获取新增诊断首次提供的真实阶段及进度，在先扩展design/tasks并strict通过后，显式启动一次生产只读完整备份；并未声称USB连接条件改变。该job在147.2秒失败，公开提示为Flash reading，1310720/4194304 bytes completed，类别operation_failed，明确no Flash was written。这表示此前五个256KB范围已完整成功，不表示失败范围内的准确中断位置，也不足以确定底层根因。没有生成完整备份或开放覆盖确认，失败后未重复完整读取。完整job状态保存于ignored `.runtime-local/phone-acceptance/staged-backup-failed-private.json`。

失败后第一次有效BLE重新绑定握手超时；切回ADB以释放串口，执行一次RTS复位并保留本机启动记录后，生产BLE绑定成功，connected=true、firmware=0.1.1、hid_ready=false、ble_state=null。未发送手机输入、未向板子刷入0.1.2。USB线材/供电/驱动原因仍未知，已请用户更换数据线并直连USB后再验收；完整备份、分层BLE与手机实机相关其他变更保持活动。

归档前 `openspec validate --all --strict --no-interactive`、`python scripts/check_changes.py` 与 `git diff --check` 通过（既有CRLF提示不影响退出码）。本变更阶段提示和脱敏行为已验证；这不代表传输故障或BLE已修复。
