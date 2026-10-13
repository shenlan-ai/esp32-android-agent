## Purpose
分别呈现经典ESP32 BLE链路、认证和键鼠通知订阅的实际状态，帮助用户定位手机输入未就绪原因，同时保持既有输入门槛和隐私边界。

## ADDED Requirements

### Requirement: Layered BLE readiness evidence
经典BLE固件 SHALL 在有效串口回复提供物理链路、认证及键盘/鼠标真实通知订阅的可选ble_state诊断，以及null或0–255整数的最近认证错误。诊断 MUST 不含MAC、密钥或私密日志，MUST 不设置通知订阅或代替既有hid_ready输入门槛。断线 SHALL 清除连接和认证状态，认证成功 SHALL 清除错误。

#### Scenario: Phone reports connected without usable HID
- **WHEN** 手机链路连接但认证或任一报告订阅未完成
- **THEN** 回复分别报告实际状态，未就绪时仍拒绝输入，不假定已连接等于可控制

#### Scenario: Authentication failed
- **WHEN** 认证回调报告失败原因
- **THEN** 诊断保留脱敏错误码，认证失败状态不开放输入，成功或断线后清除错误

### Requirement: Backward-compatible diagnostic display
主机 SHALL 只保存类型正确的允许诊断字段；缺失、非法或已断线的诊断 SHALL 公开未知。界面 SHALL 区分连接、认证和报告订阅未就绪，支持中英文及旧固件兜底；USB行为保持。诊断 MUST 不改变能力、不触发输入、配对或重试。

#### Scenario: Older firmware omits diagnostics
- **WHEN** 正常握手未提供ble_state
- **THEN** 保留原有就绪和动作规则，诊断未知并使用原提示

#### Scenario: Diagnostic claims ready but authoritative readiness is false
- **WHEN** ble_state全true而既有ble_connected为false
- **THEN** 输入仍拒绝且不列控制能力，不用诊断放宽控制门槛

#### Scenario: Reports are not subscribed
- **WHEN** 已连接且已认证，但缺少键盘或鼠标通知订阅
- **THEN** 界面提示重连并检查系统键盘/鼠标选项，不要求反复配对而不说明具体缺失
