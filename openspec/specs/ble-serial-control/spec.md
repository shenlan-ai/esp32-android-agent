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

### Requirement: Explicit backend and calibrated coordinates
用户 SHALL 显式绑定当前手机与BLE板子。坐标动作 MUST 使用该手机、完整截图尺寸及握手固件对应的校准；未校准、截图尺寸变化、固件版本失配或BLE未连接 SHALL 拒绝坐标输入。历史无固件字段校准仅适用于0.1.0；新版经典0.1.1 MUST 重新校准。主机 SHALL 保存实际握手版本，拒绝请求伪造版本；公开calibrated与坐标能力 SHALL 反映版本匹配。特殊安卓导航键未验证时不得列为BLE能力。

握手版本 MUST 为1至64字符ASCII标识，首字符为字母或数字，其余只含字母、数字、点、下划线、加号或连字符，且不是大小写无关的unknown占位。缺失或非法版本 MUST 保持未知，不转换/截断生成可匹配版本；未知版本 SHALL 拒绝保存校准和开放坐标能力，保留已有校准及不依赖坐标的键盘能力。

#### Scenario: Phone rotates
- **WHEN** 当前截图尺寸与保存校准不同
- **THEN** 拒绝坐标动作并提示重新校准

#### Scenario: Hardware disconnects
- **WHEN** BLE主模式串口或手机连接断开
- **THEN** 报告断线，不自动切换ADB控制

#### Scenario: Pacing firmware replaces an older version
- **WHEN** 当前握手固件为0.1.1而保存校准是0.1.0或无版本
- **THEN** 公开未校准且不列坐标能力，键盘仍可用，重新保存时绑定真实固件

#### Scenario: Caller supplies a different firmware version
- **WHEN** 校准请求提供与已连接固件不同的非空版本
- **THEN** 拒绝保存，不覆盖已有校准

#### Scenario: Firmware version is missing or malformed
- **WHEN** 握手缺失版本、返回unknown占位、非字符串或不符合标识边界
- **THEN** 保持版本未知，保存校准拒绝且公开未校准、不列坐标能力，已有校准保留而键盘仍可用

### Requirement: Reviewable firmware overwrite
固件构建与识别 SHALL 不覆盖现有Flash；覆盖前 MUST 提供实际芯片匹配检查、原Flash备份、校验和及明确的刷写操作。

#### Scenario: User only identifies a board
- **WHEN** 用户执行检测或构建
- **THEN** 板上现有固件保持原样

### Requirement: Transport-specific paced pointer motion
经典BLE固件 SHALL 以50ms间隔发送定位与拖动运动报告，归位完成后 SHALL 通过调度器等待600ms再定位；等待期间 MUST 无按钮按下且继续处理停止、断线和心跳。原生USB默认10ms节奏不变，键盘按下/释放节奏不变。BLE坐标/locate响应 SHALL 有60秒上限，不自动重发超时动作。

#### Scenario: Homing completes before a BLE click
- **WHEN** 经典BLE动作完成负饱和归位
- **THEN** 等待600ms后才发送正向定位报告，每次运动间隔至少50ms，定位完成后才按下

#### Scenario: Stop during the homing settle interval
- **WHEN** 归位后等待阶段收到stop或心跳失效
- **THEN** 立即取消并释放输入，不继续定位或点击，主循环没有阻塞等待

#### Scenario: Swipe uses its calibration pace
- **WHEN** BLE拖动移动时间长于请求最低时长
- **THEN** 始终沿用50ms运动间隔并报告实际耗时，主机等待有界且仍可取消

#### Scenario: USB uses shared scheduler defaults
- **WHEN** 原生USB执行定位或拖动
- **THEN** 默认继续10ms运动间隔和零归位等待，不被BLE配置改变

### Requirement: Relative reports preserve each motion vector
共享定位和拖动调度器 SHALL 按同一段的两轴比例生成有界整数报告，每轴每报告绝对值不超过8，累计终点精确等于请求向量，任意报告后的累计位置与均匀目标线段每轴误差不超过0.5个HID计数。非等比例位移 MUST 不先独立耗尽短轴再补长轴。段切换 MUST 重置插值状态，每次调度至多一个报告，并保持各传输既有节奏、最低按压时长及取消。改变运动算法的新版固件 MUST 使用不同握手版本，使旧校准按既有门禁失效；报告计数保证不得代替手机像素精度声明。

#### Scenario: An unequal-axis drag is scheduled
- **WHEN** 拖动请求包含不同大小的有符号X/Y位移
- **THEN** 两轴沿同一线段进度同步完成，逐报告保持步幅/线误差边界及精确端点

#### Scenario: Positioning changes to pressed movement
- **WHEN** 定位结束后按下并进入不同斜率的拖动段
- **THEN** 新段使用独立初始向量和进度，旧定位状态不造成跳变或错误终点

#### Scenario: Stop interrupts interpolation
- **WHEN** 插值运动中动作被取消或心跳失效
- **THEN** 后续调度不发送余下运动，保持输入释放及会话失效语义

### Requirement: Bounded continuous multi-point HID stroke
经典BLE固件 SHALL 明确声明path并严格接受2–20个0–4000整数计数点，所有段运动报告总数最多500，最低总按压时长50–5000ms。调度 MUST 定位首点后仅按下一次，逐段同步插值并最终释放一次，段间不归位、不松开，每次advance至多一运动报告。重复/闭合点 MUST 安全处理。超预算、非法或多余字段 MUST 在accepted前拒绝；取消、心跳失效和断线 MUST 清空剩余段并按既有语义释放。新能力 MUST 提升固件版本，旧校准失效。
#### Scenario: A curve crosses multiple segments
- **WHEN** 合法path含正负轴及重复点
- **THEN** 鼠标保持按住，逐段到达请求点，最后一次释放，最坏BLE执行在既有60秒主机期限内
#### Scenario: Stop interrupts a later path segment
- **WHEN** 路径按住运行时停止或会话失效
- **THEN** 后续段不发送，释放遵循真实连接状态，不重放该笔划
#### Scenario: Path exceeds the report budget
- **WHEN** 全部段需要超过500个有界运动报告
- **THEN** 请求被拒绝且未执行任何路径输入
