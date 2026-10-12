## MODIFIED Requirements
### Requirement: Owned firmware job and exclusive device maintenance
固件job SHALL 由应用拥有的后台任务执行，与HID/ADB输入、任务启动/恢复、选择设备、控制绑定及串口配网互斥；网页断开/刷新和手机紧急停止 MUST 不取消写Flash。只读识别/备份可取消，写入/校验取消 SHALL 拒绝。优雅关闭 MUST 等待拥有的操作完成，超时或失败不得自动重试。

#### Scenario: Browser disconnects during writing
- **WHEN** 已授权写入的HTTP请求或网页关闭
- **THEN** 后台写入/校验继续，GET可重新获取阶段和结果

#### Scenario: Phone stop during firmware writing
- **WHEN** 用户按Esc或手机紧急停止
- **THEN** 释放手机输入但不终止固件工具，也不排队在刷写结束后执行旧动作

#### Scenario: Read-only operation completes while cancellation arrives
- **WHEN** 支持Python版本中只读操作完成与显式取消同时到达
- **THEN** 系统 MUST 保留取消并回收相关等待或子进程，写Flash仍由原拥有任务规则保护
