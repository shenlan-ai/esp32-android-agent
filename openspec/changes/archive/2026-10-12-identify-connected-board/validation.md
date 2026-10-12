# Validation

- `openspec.cmd validate identify-connected-board --strict --no-interactive`：通过。
- `python -m unittest discover -s scripts/tests`：13项通过（含7项识别测试）。
- `python scripts/identify_board.py`：status identified，COM5，ESP32-D0WD-V3 revision v3.1，4MB，BLE HID 路线。
- `esptool.exe --port COM5 --no-stub chip-id` 与 `flash-id`：独立实机复核通过，无擦除或 Flash 写入。
- `python scripts/check_changes.py`：范围通过。
- Microsoft 官方 CAB 的 SHA1 与下载目录一致；CAT Authenticode 状态 Valid；驱动正常 UAC 安装后 PnP 错误码0。

限制：芯片信息不能确定 PCB 商品名；未刷写固件、未与安卓手机蓝牙配对。具体 HID 适配另立变更。
