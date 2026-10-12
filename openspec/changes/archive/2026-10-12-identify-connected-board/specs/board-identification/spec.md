## Purpose

帮助用户根据真实连接设备的串口状态、ESP 芯片和 Flash 信息选择可用固件，防止把 USB 转串口桥误当成板型，并在驱动缺失或商品名无法判定时给出准确的恢复说明。

## ADDED Requirements

### Requirement: Evidence-based non-writing identification
识别流程 MUST 区分 USB 桥、串口、ESP 芯片、Flash 容量和商品板型，芯片识别 SHALL 不擦除或写入 Flash。没有证据时不得声称确定具体商品板型。

#### Scenario: CP2102 has no COM port
- **WHEN** Windows 报告驱动缺失且设备使用 CP2102
- **THEN** 提示安装官方驱动并等待串口恢复，不推断主芯片为某一 ESP32 型号

#### Scenario: Chip is readable but PCB model is unknown
- **WHEN** 读取到芯片和 Flash 信息
- **THEN** 依据芯片选择构建配置，商品板型仍标记未确认，除非有额外可靠信息

#### Scenario: Unknown chip family
- **WHEN** esptool 返回未明确支持的芯片系列
- **THEN** 保留原始芯片名称并返回未支持状态，不猜测 USB 或 BLE HID 路线

#### Scenario: Multiple serial devices
- **WHEN** 主机上存在多个候选开发板串口
- **THEN** 要求显式选择端口；自动选择 SHALL 排除不匹配已知 USB/UART 标识的串口
