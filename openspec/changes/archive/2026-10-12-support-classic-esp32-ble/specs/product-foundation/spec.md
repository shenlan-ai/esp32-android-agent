## MODIFIED Requirements

### Requirement: Two explicit control paths
产品 SHALL 提供 ADB 体验路径和 ESP32 HID 主路径，明确展示当前控制方式，并禁止未经用户操作自动切换控制后端。原生USB HID的ESP32主路径 SHALL 使用无线ADB获取画面；通过电脑串口连接的BLE HID主路径 SHALL 允许USB或无线ADB画面。

#### Scenario: User starts without a board
- **WHEN** 用户选择 ADB 体验路径
- **THEN** 可在无 ESP32 的情况下验证画面、基础控制和模型任务

#### Scenario: Hardware control loses connection
- **WHEN** ESP32 控制连接中断
- **THEN** 系统报告断线并停止当前操作，不自动改用 ADB 执行

#### Scenario: Classic ESP32 uses BLE
- **WHEN** 板子通过串口连接电脑、通过BLE连接手机
- **THEN** 允许手机使用USB或无线ADB采集，无需板子Wi-Fi配置
