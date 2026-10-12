## MODIFIED Requirements
### Requirement: Interruptible control and honest results
长动作 SHALL 按短周期调度，同时处理停止和心跳。BLE断线或主机心跳失效 MUST 清空动作、清理输入状态并作废会话。主机 MUST 不自动重试结果未知的动作；命令完成不等于手机目标达成。Python3.10及以上版本的异步响应超时 MUST 使连接失效并报告动作结果未知。

#### Scenario: Stop during drag
- **WHEN** 鼠标拖动执行中收到stop
- **THEN** 停止后续移动并释放鼠标与键盘，主机收到释放状态

#### Scenario: Host disappears
- **WHEN** 超过1500ms未收到有效心跳
- **THEN** 固件终止动作、释放输入且旧会话失效

#### Scenario: Drag duration and fixed report pace
- **WHEN** 拖动指定的最低时长短于固定报告节奏所需的移动时间
- **THEN** 保持校准时相同的报告节奏并返回实际执行与按下时长，不声称精确达到请求时序

#### Scenario: BLE notification is unavailable
- **WHEN** HID报告未订阅或GATT发送失败
- **THEN** 不将动作报告为done，清理输入并使故障会话失效，提示重新观察和连接

#### Scenario: Host action response times out on a supported runtime
- **WHEN** Python3.10或更新版本已发送动作但未收到done
- **THEN** 失效连接、报告结果未知且只发送一次动作，不泄漏异步超时异常到调用者

#### Scenario: Completion races with caller cancellation
- **WHEN** 支持Python版本中有时限的等待完成与外层取消同时到达
- **THEN** 系统 MUST 保留取消并回收等待任务，不能继续执行循环或阻塞停止
