## ADDED Requirements

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

## MODIFIED Requirements

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
