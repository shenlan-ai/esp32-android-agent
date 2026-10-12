# task-history Specification

## Purpose
为用户和贡献者提供可观察、可排查的任务执行证据，展示步骤说明、模型与动作耗时及截图，同时保护凭据，允许选择本机截图留存并导出已有任务记录。

## Requirements

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

### Requirement: Local traces without credentials
系统 SHALL 在本机记录任务目标、步骤、错误与用量，截图落盘仅在用户启用时进行；API Key、访问令牌及配对码 MUST 不进入记录或错误响应。

#### Scenario: Screenshots are disabled
- **WHEN** 执行任务并未启用截图保存
- **THEN** 当前任务可以预览步骤画面，磁盘记录不包含截图文件

### Requirement: Safe trace export
系统 SHALL 允许查看与导出已有任务记录，拒绝越出记录目录的路径；清空当前任务记录 SHALL 不删除已有磁盘历史。

#### Scenario: Export path attempts traversal
- **WHEN** 请求包含越目录路径
- **THEN** 请求被拒绝，不读取目录外文件
