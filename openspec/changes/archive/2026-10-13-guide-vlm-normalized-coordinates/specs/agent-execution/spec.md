## ADDED Requirements

### Requirement: Action vision uses normalized coordinate guides
动作模型 SHALL 接收与完整截图0..1000空间一致的可视坐标引导图及明确的坐标上下文。引导 MUST 保持图像大小与截图映射，MUST 不改原始截图、规划/独立核验图片或HID校准；严格动作参数验证保持。

#### Scenario: Model chooses a visible target
- **WHEN** 动作模型读取当前截图
- **THEN** 能参考归一化坐标尺，选择的参数仍按完整截图映射，而非直接使用缩小图像像素

#### Scenario: Independent verifier inspects the result
- **WHEN** 核验模型对操作前后图片判断结果
- **THEN** 收到未加引导的原图，不将辅助线或标签误判为手机内容
