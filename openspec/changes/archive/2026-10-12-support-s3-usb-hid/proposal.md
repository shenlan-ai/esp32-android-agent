## Why

现有经典 ESP32 BLE 已编译并验证串口，但正式设计中的 S3 原生 USB 主控制路线尚未实现。开源用户需要无需修改源码的板上配置、明确连接模式和可中断控制。

## What Changes

- 提供 ESP32-S3 DevKitC-1 N8、XIAO ESP32S3 和 S3 Zero 4MB 的固定 PlatformIO 配置，复用真实动作调度及参数验证。
- 实现 USB 键鼠、USB CDC 配置、NVS 原子配置、Wi-Fi 出站连接及随机挑战 HMAC 配对；主机板子端口与本机网页分离。
- 主机新增 USB 控制模式、独立校准、无线 ADB 约束、网页配网和显式重连。断线不会自动切换控制或重放动作。
- 新增无设备 TCP 协议测试、配置测试、三个板型构建及使用说明。当前 COM5 固件不写入，不将构建或模拟当作 S3 实机验收。

## Capabilities

### New Capabilities
- `usb-hid-control`: 原生 USB 键鼠、板上配置和认证控制链路。

### Modified Capabilities
- `local-settings`: 增加配对凭据和按板子/手机绑定的 USB 校准，公开接口掩码。

## Impact

影响 hardware/usb_bridge、BLE 协议主机共享处理、设备会话、网页连接向导、配置和测试文档。不引入安卓 App、Node 运行依赖或自动刷写。
