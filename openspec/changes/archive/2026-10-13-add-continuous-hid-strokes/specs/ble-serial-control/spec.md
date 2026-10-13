## ADDED Requirements
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
