# Validation

2026-10-12，Windows，COM5真实ESP32-D0WD-V3 v3.1、4MB。用户明确回复“现在刷入并验证板上通信”。

## 刷写

- `.venv/Scripts/python.exe scripts/flash_board.py --port COM5 --write --confirm-overwrite`：退出0。芯片与构建产物预检通过；重新备份完整4MB后写bootloader、partitions、boot_app0及firmware，esptool各段写后hash校验通过，最后正常复位。
- 新备份：`.runtime-local/firmware-backups/esp32-20261012-205205.bin`，4194304字节，SHA256 `96A8ED454EC2A1D74F480824CE91FDBD8919E22C5AFD98AA55D926BB46F5204D`，与首次备份一致。备份和设备日志未提交。
- 固件：0.1.0，1142288字节，SHA256 `86F9B27A01B45A5FDD1A609882F8EC0959B3A01260C85F7A87A0B48D886C044C`。本变更没有修改固件或服务端实现。
- 详细本机刷写日志：`.runtime-local/flash-com5.log`。

## 真实串口与主机

- `.venv/Scripts/python.exe scripts/check_board_link.py --port COM5`：退出0。
- 10项协议检查通过：hello芯片/32位随机会话、status、错误版本拒绝、旧会话拒绝、非法JSON拒绝、超长行后恢复、停止准确释放字段、心跳维持会话、停止心跳1.8s后会话作废、新hello恢复。
- 2项生产SerialBridge检查通过：自动心跳2.2s后status/stop仍可用；关闭后重新打开并成功通信。
- 板回应芯片esp32、固件0.1.0、BLE名称Android Agent BLE、ble_connected=false。无手机时停止返回board_state_cleared_phone_disconnected。
- 报告在`.runtime-local/board-link-report.json`。脚本不发送任何HID动作；phone_input_verified=false。

## 开发检查与限制

- `.venv/Scripts/ruff.exe check scripts/check_board_link.py`：通过；`--help`正常，不访问设备。
- `openspec validate verify-connected-board --strict --no-interactive`与`python scripts/check_changes.py`：通过；归档后全规格和归档检查通过。
- 前一开发变更已验证54个pytest、19个unittest（含固件原生22场景）、3个Node测试与固件编译；本变更未修改这些实现，不重复整套测试。
- 手机尚未连接ADB或BLE；没有实测手机输入、鼠标精度、拖动中释放、手机断线或Android15–17厂商兼容性。不将无活动动作时的停止/看门狗测试扩大为这些结论。
- 自动任务变更implement-verified-agent继续保持活动，不由当前实机通信验收宣称完成。
