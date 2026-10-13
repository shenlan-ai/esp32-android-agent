# manual-control Specification

## Purpose
为不配置模型的用户提供可验证的基础安卓手动操作，严格约束动作与输入参数，避免命令注入、并发手势和错误重放，并让停止能够取消待处理动作。

## Requirements

### Requirement: Validated serial manual actions
系统 SHALL 支持点按、滑动、长按、滚动、ASCII 文本、已支持按键、主页、返回和最近任务；非法动作 MUST 在输入设备前拒绝，手势串行执行。

#### Scenario: Text contains shell metacharacters
- **WHEN** 用户输入合法 ASCII 文本中的引号或分号
- **THEN** 该内容作为文本安全传入安卓，不成为额外 shell 命令

#### Scenario: Unicode input is requested
- **WHEN** 未启用 Unicode 扩展时输入中文
- **THEN** 返回明确能力提示，不发送损坏文字

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
