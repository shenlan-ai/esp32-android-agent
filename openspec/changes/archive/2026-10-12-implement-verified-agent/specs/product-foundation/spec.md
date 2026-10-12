## ADDED Requirements

### Requirement: Recent Android and native USB board targets
产品 MUST 将官方最近稳定三代 Android 作为适配目标，当前为 Android 15/API35、16/API36、17/API37，并记录具体机型验证情况。硬件主路径 SHALL 优先覆盖 ESP32-S3 DevKitC-1、XIAO ESP32S3 和 ESP32-S3 Zero 等原生 USB 板型，不将经典 ESP32-WROOM 描述为可直接运行 USB HID 固件。

#### Scenario: A recent Android phone is connected
- **WHEN** 接入上述目标版本的手机
- **THEN** 使用标准 ADB 和 HID 能力处理，不依赖单一厂商私有接口；未验收机型仍标记待验证

#### Scenario: A board lacks native USB
- **WHEN** 用户选择经典 ESP32-WROOM
- **THEN** 文档说明使用独立的 BLE 固件与电脑串口路线，不推荐刷入原生 USB 固件；构建与实机状态分别记录
