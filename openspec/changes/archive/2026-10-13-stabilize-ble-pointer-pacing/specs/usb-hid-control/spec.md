## MODIFIED Requirements

### Requirement: Explicit phone binding and USB calibration
系统 SHALL 提供 usb 控制模式，只绑定在线无线 ADB 手机并要求用户确认板子插入该手机。校准 MUST 按板子身份、手机、画面尺寸及实际握手固件区分，与 BLE 校准独立；未校准或固件版本失配不开放坐标动作。保存校准 MUST 使用有效握手版本且拒绝请求伪造版本。

握手版本 MUST 为1至64字符ASCII标识，首字符为字母或数字，其余只含字母、数字、点、下划线、加号或连字符，且不是大小写无关的unknown占位。缺失或非法版本 MUST 保持未知，不转换/截断生成可匹配版本；未知版本 SHALL 拒绝保存校准和开放坐标能力，保留已有校准及不依赖坐标的键盘能力。历史无固件字段校准仅适用于0.1.0。

#### Scenario: USB ADB selected
- **WHEN** 用户尝试给 USB ADB 设备绑定 S3 USB 控制
- **THEN** 系统提示先建立无线 ADB，不把同一 USB 口假定可同时充当设备和主机

#### Scenario: Board reconnects or screen rotates
- **WHEN** 板子建立新 TCP 会话或画面尺寸改变
- **THEN** 不自动恢复旧动作，用户显式重绑；旧尺寸校准拒绝坐标动作

#### Scenario: Firmware version is missing or malformed
- **WHEN** 认证后的USB握手缺失版本、返回unknown占位、非字符串或不符合标识边界
- **THEN** 保持版本未知，保存校准拒绝且公开未校准、不列坐标能力，已有校准保留而键盘仍可用

#### Scenario: Firmware version changes
- **WHEN** 实际握手版本与已有校准不匹配或保存请求提供不同非空版本
- **THEN** 不开放坐标能力或覆盖现有校准，用户重新实测校准后保存实际握手版本
