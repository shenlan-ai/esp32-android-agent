## Purpose

使用户可以通过自然语言目标操作安卓手机，同时确保模型动作符合设备能力、依据有效画面执行并验证结果，支持预算限制、暂停接管和恢复，不将不确定操作或模型自述视为成功。

## ADDED Requirements

### Requirement: Structured capability-aware single-step execution
系统 SHALL 仅接受通过严格参数校验且属于当前控制器能力的模型动作，每次执行一个改变界面的动作；错误输出 MUST 在输入设备前被拒绝并限次恢复。

#### Scenario: Model returns unsupported or malformed action
- **WHEN** 模型返回未知动作、超范围坐标或非法 JSON
- **THEN** 不执行该动作，记录可理解错误并在预算内重新观察或规划

### Requirement: Fresh observation and explicit outcome validation
系统 MUST 在执行前检查决策画面的几何及相关内容是否失效，动作后取得新画面并验证预期结果。模型宣告完成 SHALL 经过独立目标验证。

#### Scenario: Screen changes while model thinks
- **WHEN** 模型返回前目标区域显著变化或旋转
- **THEN** 旧动作不执行，重新观察

#### Scenario: Model says done without reaching the goal
- **WHEN** 独立目标验证未确认目标达到
- **THEN** 任务不标记完成，继续有限恢复或结束失败

### Requirement: Pause takeover and safe resume
系统 SHALL 支持暂停并释放输入，在暂停后允许手动操作；继续时重新观察与规划。运行中 MUST 拒绝并发手动输入和设备切换。

#### Scenario: User takes over during a model request
- **WHEN** 用户请求暂停
- **THEN** 请求取消，输入释放，任务保留为暂停状态，继续时不重放旧建议

### Requirement: Bounded execution and uncertain outcome recovery
系统 SHALL 限制动作数量、活动运行时间、连续错误和模型调用数量，统计实际提供的 Token 用量；未知用量 MUST 标记估算。画面或控制断线 SHALL 暂停并要求恢复，不自动重放结果未知的输入。

#### Scenario: Device drops after an input
- **WHEN** 命令结果不确定
- **THEN** 任务暂停并记录该状态，恢复后根据新画面决策

#### Scenario: Task exceeds its configured limit
- **WHEN** 超过活动时限、动作上限或用量阈值
- **THEN** 结束任务并释放输入，保留原因与已有记录
