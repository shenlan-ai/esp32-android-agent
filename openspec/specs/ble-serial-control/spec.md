# ble-serial-control Specification

## Purpose
为经典 ESP32 提供无需板子 Wi-Fi 的串口 BLE 键鼠控制，明确连接、校准、可中断动作、故障释放和固件覆盖边界，支持开源用户使用常见4MB开发板。

## Requirements

### Requirement: Serial BLE bridge
系统 SHALL 提供适用于经典ESP32 4MB的BLE鼠标键盘固件，允许用户通过电脑串口连接板子，并在安卓系统蓝牙设置中主动配对。串口协议 MUST 限制消息长度、参数、版本、会话和命令编号。

#### Scenario: Unsupported or stale protocol
- **WHEN** 主机提交不匹配的版本或旧会话动作
- **THEN** 固件拒绝执行并返回明确错误

#### Scenario: Duplicate command
- **WHEN** 同一会话收到已接受的命令编号
- **THEN** 返回状态或已记录结果，不再次执行输入

### Requirement: Interruptible control and honest results
长动作 SHALL 按短周期调度，同时处理停止和心跳。BLE断线或主机心跳失效 MUST 清空动作、清理输入状态并作废会话。主机 MUST 不自动重试结果未知的动作；命令完成不等于手机目标达成。

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

### Requirement: Explicit backend and calibrated coordinates
用户 SHALL 显式绑定当前手机与BLE板子。坐标动作 MUST 使用该手机及完整截图尺寸对应的校准；未校准、截图尺寸变化或BLE未连接 SHALL 拒绝输入。特殊安卓导航键未验证时不得列为BLE能力。

#### Scenario: Phone rotates
- **WHEN** 当前截图尺寸与保存校准不同
- **THEN** 拒绝坐标动作并提示重新校准

#### Scenario: Hardware disconnects
- **WHEN** BLE主模式串口或手机连接断开
- **THEN** 报告断线，不自动切换ADB控制

### Requirement: Reviewable firmware overwrite
固件构建与识别 SHALL 不覆盖现有Flash；覆盖前 MUST 提供实际芯片匹配检查、原Flash备份、校验和及明确的刷写操作。

#### Scenario: User only identifies a board
- **WHEN** 用户执行检测或构建
- **THEN** 板上现有固件保持原样
