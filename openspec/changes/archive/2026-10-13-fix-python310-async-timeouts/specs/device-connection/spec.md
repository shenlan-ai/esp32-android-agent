## MODIFIED Requirements
### Requirement: Explicit device selection and diagnosis
系统 SHALL 列出设备及状态，仅允许选择已授权且在线的设备；多个设备时 MUST 要求明确选择，不将 offline 或 unauthorized 设备视为可操作。

#### Scenario: Multiple devices are online
- **WHEN** 已连接多个设备且用户尚未选择
- **THEN** 画面与动作不自动发送给任一设备，控制台提示选择

#### Scenario: ADB is unavailable
- **WHEN** 工具未安装或执行失败
- **THEN** 服务与网页仍可启动，返回可操作的诊断信息

#### Scenario: Read-only operation completes while cancellation arrives
- **WHEN** 支持Python版本中只读操作完成与显式取消同时到达
- **THEN** 系统 MUST 保留取消并回收相关等待或子进程，写Flash仍由原拥有任务规则保护
