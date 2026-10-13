## ADDED Requirements

### Requirement: Native USB preserves relative motion vectors
原生USB SHALL 使用共享整数线段插值，使不同两轴位移按相同段进度同步完成；每轴每报告绝对值不超过8，累计目标线段误差每轴不超过0.5个HID计数，最终位移精确。固件 MUST 保持10ms运动节奏、可取消单步调度和严格参数校验，算法改变 MUST 提升握手及CDC版本并要求重新校准；未实测的手机像素精度保持未验证。

#### Scenario: USB executes a shallow signed vector
- **WHEN** 原生USB执行长轴与短轴不同的定位或拖动
- **THEN** 实际共享调度报告保持线段比例及端点，旧固件校准不开放新版坐标能力
