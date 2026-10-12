## MODIFIED Requirements
### Requirement: Authenticated bounded board connections
系统 SHALL 使用独立板子 TCP 端口和每板随机凭据，通过随机挑战 HMAC 认证板子身份；默认监听关闭，用户显式启用。未认证连接 MUST 有时间/数量/长度上限，活跃认证连接不被新连接替代。Python3.10及以上版本 MUST 一致关闭超时认证连接、回收任务且不泄漏未处理异步超时。

#### Scenario: Wrong or replayed proof
- **WHEN** 对端提交错误身份、错误证明或上次挑战的证明
- **THEN** 连接被关闭，不能获取控制会话或执行动作

#### Scenario: Board port unavailable
- **WHEN** 板子端口被其他服务占用
- **THEN** USB 路线报告不可用，ADB 工作台仍可启动

#### Scenario: Silent authentication peer times out
- **WHEN** 未认证客户端读取挑战后保持沉默，认证时限到达
- **THEN** 关闭该连接并释放占用，无未处理异常且不影响其他客户端

### Requirement: Interruptible HID with explicit outcomes
固件 SHALL 使用 JSON v1、随机会话、动作编号去重和一个非阻塞动作；持续处理停止和 1500ms 心跳看门狗。网络、USB 或心跳失效 MUST 取消动作并释放键鼠；主机取消或超时不重放，结果区分接受、报告完成、释放未确认和手机画面核验。Python3.10及以上版本的网络发送超时 MUST 使连接失效、报告未知且不重放；网络关闭等待 MUST 有界。

#### Scenario: Stop during drag
- **WHEN** 停止命令到达而拖动仍在调度
- **THEN** 当前动作取消，清空输入，返回释放是否已提交 USB 主机，不等到整个拖动结束

#### Scenario: Action times out
- **WHEN** 已发送动作未收到完成响应
- **THEN** 连接失效并提示结果未知，恢复先观察，不重新发送该动作

#### Scenario: TCP write or close stalls
- **WHEN** 网络发送或关闭的异步等待超时
- **THEN** 写入只尝试一次并报告未知，关闭在预算内返回，支持版本均完成任务回收

#### Scenario: Completion races with caller cancellation
- **WHEN** 支持Python版本中有时限的等待完成与外层取消同时到达
- **THEN** 系统 MUST 保留取消并回收等待任务，不能继续执行循环或阻塞停止
