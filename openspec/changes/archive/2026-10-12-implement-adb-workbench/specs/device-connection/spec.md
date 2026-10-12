## Purpose

让用户在不修改源码和不配置模型的情况下发现、授权并选择自己的安卓设备，明确区分 USB、无线配对与无线连接，以及多个设备、未授权和工具缺失等可恢复状态。

## ADDED Requirements

### Requirement: Explicit device selection and diagnosis
系统 SHALL 列出设备及状态，仅允许选择已授权且在线的设备；多个设备时 MUST 要求明确选择，不将 offline 或 unauthorized 设备视为可操作。

#### Scenario: Multiple devices are online
- **WHEN** 已连接多个设备且用户尚未选择
- **THEN** 画面与动作不自动发送给任一设备，控制台提示选择

#### Scenario: ADB is unavailable
- **WHEN** 工具未安装或执行失败
- **THEN** 服务与网页仍可启动，返回可操作的诊断信息

### Requirement: Wireless pairing and connection are distinct
系统 SHALL 区分配对地址、配对码和连接地址，校验输入，显示发现服务及连接结果，且错误与日志不得泄露配对码。

#### Scenario: Pairing succeeds
- **WHEN** 用户输入合法配对地址和配对码
- **THEN** 系统完成配对并提示使用连接端口继续连接，不把配对端口当连接端口

#### Scenario: Invalid address is provided
- **WHEN** 地址包含命令字符或无效端口
- **THEN** 在执行外部工具前拒绝输入
