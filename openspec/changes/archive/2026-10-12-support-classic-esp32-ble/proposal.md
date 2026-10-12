## Why

当前实机是 ESP32-D0WD-V3 revision v3.1、4MB Flash，不能使用参考项目的 S3 USB HID 固件。开源用户应能用手头常见经典 ESP32，且无需修改源码或配置板子 Wi-Fi。

## What Changes

- 为通用经典 ESP32 添加可编译 BLE 键鼠固件，通过电脑 USB 串口传输指令，手机通过 BLE 配对。
- 增加版本化 JSON 行协议、会话和命令编号、明确结果、非阻塞长动作、停止和心跳失效释放。
- 主机增加串口控制器、连接向导、校准和显式模式切换；BLE 不支持的 Android 导航动作不伪装为已支持。
- 更新架构、兼容文档与识别结果；固定构建依赖并编译当前4MB配置。刷写覆盖前需保存原固件并单独获得用户对覆盖的确认。

## Capabilities

### New Capabilities
- `ble-serial-control`: 通过主机串口和 BLE HID 操作手机，带停止与故障恢复。

### Modified Capabilities
- `product-foundation`: BLE 板子在电脑上时允许 USB 或无线 ADB 画面，原生 USB HID 路线仍使用无线 ADB。
- `board-identification`: 芯片识别与可用固件配置分开呈现，记录当前实机配置。

## Impact

增加 pyserial 与 PlatformIO 开发构建；使用 Arduino ESP32 内置 BLE HID，不引入手机伴侣 App。当前阶段只提供经典 ESP32 固件；S3/S2 构建后续单独交付。所有手机配对、鼠标校准和 Android 15–17 实机行为仍需测试，不以编译成功代替。
