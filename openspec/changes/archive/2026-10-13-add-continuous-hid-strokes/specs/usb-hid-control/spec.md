## ADDED Requirements
### Requirement: Native USB continuous stroke parity
S3原生USB SHALL 声明并采用共享有界多点path能力，保持2–20点、严格0–4000整数、500报告限制、一次按下/释放及10ms节奏，主机30秒期限及原认证/会话/取消规则不变。固件 MUST 提升握手及CDC版本并要求新校准，未经实机验证不声称手机连续绘图兼容。
#### Scenario: USB draws a closed path
- **WHEN** 已认证USB控制器收到合法闭合路径
- **THEN** 共享调度器连续通过各点并回到起点后释放，取消立即停止余下段
