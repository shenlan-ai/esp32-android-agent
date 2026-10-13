## ADDED Requirements

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
