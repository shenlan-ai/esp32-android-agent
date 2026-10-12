# usb-hid-control Specification

## Purpose
让 ESP32-S3 通过原生 USB 键鼠控制无线 ADB 手机，提供无需重编译的板上配网、独立认证连接、按板子绑定的校准和可中断动作；明确区分报告提交、释放确认与手机画面验收，断线后须显式重绑。

## Requirements

### Requirement: Native USB board profiles and configuration
系统 SHALL 提供固定的 DevKitC-1 N8、XIAO ESP32S3、S3 Zero 4MB 构建配置；运行时通过 USB CDC 写入 Wi-Fi、主机地址、端口和配对密钥，以 NVS 单条配置保存。配置接口 MUST 校验 S3 固件身份、参数长度和目标串口，不回显秘密，不通过串口执行 HID 动作。

#### Scenario: Configure without rebuilding
- **WHEN** 用户连接已刷入支持固件的 S3 并提交合法配网参数
- **THEN** 配置保存、板子重新连接主机，无需修改源码或编译，公开结果只有板子身份和配置状态

#### Scenario: Classic board selected by mistake
- **WHEN** 配网读取到经典 ESP32 或其他固件
- **THEN** 主机在发送 configure 前拒绝，现有固件和配置保留

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

### Requirement: Explicit phone binding and USB calibration
系统 SHALL 提供 usb 控制模式，只绑定在线无线 ADB 手机并要求用户确认板子插入该手机。校准 MUST 按板子身份、手机和画面尺寸区分，与 BLE 校准独立；未校准不开放坐标动作。

#### Scenario: USB ADB selected
- **WHEN** 用户尝试给 USB ADB 设备绑定 S3 USB 控制
- **THEN** 系统提示先建立无线 ADB，不把同一 USB 口假定可同时充当设备和主机

#### Scenario: Board reconnects or screen rotates
- **WHEN** 板子建立新 TCP 会话或画面尺寸改变
- **THEN** 不自动恢复旧动作，用户显式重绑；旧尺寸校准拒绝坐标动作

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
