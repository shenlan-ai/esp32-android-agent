## MODIFIED Requirements
### Requirement: Bounded execution and uncertain outcome recovery
系统 SHALL 限制动作数量、活动运行时间、连续错误和模型调用数量，统计实际提供的 Token 用量；未知用量 MUST 标记估算。画面或控制断线 SHALL 暂停并要求恢复，不自动重放结果未知的输入。支持的Python3.10及以上版本 MUST 一致处理异步活动时限，取消超时工作、释放输入并保留实际时限原因。

#### Scenario: Device drops after an input
- **WHEN** 命令结果不确定
- **THEN** 任务暂停并记录该状态，恢复后根据新画面决策

#### Scenario: Task exceeds its configured limit
- **WHEN** 超过活动时限、动作上限或用量阈值
- **THEN** 结束任务并释放输入，保留原因与已有记录

#### Scenario: Active deadline expires on Python 3.10
- **WHEN** Python3.10运行的任务因asyncio.wait_for活动时限超时
- **THEN** 结束任务并记录time limit原因，取消工作和释放会话，不报告为未识别的普通错误

#### Scenario: Completion races with caller cancellation
- **WHEN** 支持Python版本中有时限的等待完成与外层取消同时到达
- **THEN** 系统 MUST 保留取消并回收等待任务，不能继续执行循环或阻塞停止
