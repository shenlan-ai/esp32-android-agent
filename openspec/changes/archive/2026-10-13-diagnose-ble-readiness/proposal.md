## Why

真实Redmi Note14 / Android15显示Android Agent BLE已连接，而BLE0.1.1的hid_ready=false。用户确认重连并显式重新绑定后仍不就绪，现有布尔值无法区分链路、认证和两种报告订阅。固定Arduino BLE库已在连接时请求加密，不能未经证据重复添加加密请求或直接开启通知绕过手机订阅。

## What Changes

- BLE0.1.2的串口回复提供脱敏分层状态：物理链路、认证、键盘/鼠标订阅及最近认证错误码。
- 主机保存可选诊断快照，旧固件/非法诊断保持未知，界面分别提示连接、认证和报告订阅未就绪。
- 诊断不能开放能力或覆盖hid_ready，USB和动作调度不变，不自动输入或重连。
- 真实共享报告序列化、主机接收及界面选择逻辑测试，编译经典固件并准备可核验目录；刷写仍须本次完整备份和明确覆盖确认。

## Capabilities

### Added Capabilities
- ble-readiness-diagnostics: 可选、脱敏且不改变控制门槛的分层诊断。

## Impact

经典BLE固件、串口主机、静态状态提示、相关测试与协议/使用文档。与活动stabilize-ble-pointer-pacing共享文件，但保持50ms/600ms节奏不变。此变更不证明重连故障已修复，实测原因仍需新版证据。
