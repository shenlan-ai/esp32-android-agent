## ADDED Requirements

### Requirement: Chip evidence and firmware profile are separate
识别文档 SHALL 将芯片能力、可构建固件和手机实测状态分别记录；通用经典ESP32固件 SHALL 明确4MB配置和非原生USB HID控制路线，不要求推测PCB商品名。

#### Scenario: Current classic board
- **WHEN** 读取到ESP32-D0WD-V3 v3.1及4MB Flash
- **THEN** 指向通用经典ESP32 BLE固件，并分别列明构建与手机测试状态
