## MODIFIED Requirements

### Requirement: Stop cancels pending actions
系统 SHALL 取消当前受管理操作和排队动作，尽力释放输入，不因超时自动重放点击或输入。停止结果 MUST 区分已取消与设备端释放是否可确认。明确session停止导致的手动动作或定位请求取消 SHALL 返回HTTP409及可理解的取消提示，MUST 不返回500或声称输入未发生。Agent内部和非停止的外层取消 MUST 继续传播取消语义。

#### Scenario: Stop happens during a gesture
- **WHEN** 用户请求停止
- **THEN** 待执行动作取消，当前进程受控清理，记录设备侧释放结果和实际限制

#### Scenario: Manual HTTP request is interrupted by stop
- **WHEN** 已开始的手动动作或定位被session停止取消
- **THEN** 该请求返回409，提示已取消并先观察手机，停止接口单独返回释放结果，无自动重发

#### Scenario: Caller cancels without a session stop
- **WHEN** 请求或Agent调用在session epoch不变时被外层取消
- **THEN** 保留CancelledError，不转换为人工停止或继续执行
