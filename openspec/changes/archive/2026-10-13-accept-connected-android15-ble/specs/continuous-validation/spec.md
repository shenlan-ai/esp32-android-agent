## ADDED Requirements

### Requirement: Explicit local physical-input test surface
项目 SHALL 提供贡献者显式启动的本机手机输入测试页面，不自动控制手机、不调用模型、不进入默认CI设备流程。页面 MUST 无外部资源与提交型表单，记录有界的真实指针/键盘事件及本地测试值，用于人工与截图交叉核验。

#### Scenario: Contributor prepares a paired phone
- **WHEN** 贡献者启动fixture并通过已授权ADB reverse在手机打开页面
- **THEN** 可在同一实际控制模式检查目标命中、手势、ASCII和停止；报告具体型号、版本、模式与未执行项，不以页面可访问证明输入通过

#### Scenario: Report is too large
- **WHEN** 页面或客户端提交超出大小/事件数量限制的记录
- **THEN** 服务拒绝超大请求并维持有界缓冲，不执行任何手机动作
