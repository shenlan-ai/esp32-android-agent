## MODIFIED Requirements
### Requirement: Real-time bounded task history
系统 SHALL 展示任务状态、计划、步骤、动作结果和耗时，通过事件更新并在重连后恢复快照；订阅者队列 MUST 有界且不阻塞执行。Python3.10及以上版本的SSE空闲超时 SHALL 发送保活心跳并保持订阅，后续事件仍可交付。

#### Scenario: A browser reconnects during a task
- **WHEN** 事件连接重新建立
- **THEN** 浏览器取得当前完整快照并继续接收新事件，不要求重新执行任务

#### Scenario: Idle event stream sends a heartbeat
- **WHEN** 事件队列在保活时限内没有更新
- **THEN** 发送心跳而不结束生成器，后续事件继续交付，关闭生成器后释放订阅

#### Scenario: Completion races with caller cancellation
- **WHEN** 支持Python版本中有时限的等待完成与外层取消同时到达
- **THEN** 系统 MUST 保留取消并回收等待任务，不能继续执行循环或阻塞停止
