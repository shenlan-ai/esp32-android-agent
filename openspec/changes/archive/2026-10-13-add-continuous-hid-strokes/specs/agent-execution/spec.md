## ADDED Requirements
### Requirement: General continuous drawing actions
模型动作 SHALL 支持严格整数2–20点path及中心/半径circle；仅当当前HID固件声明path、版本及当前手机校准有效时提供。圆形 SHALL 按完整画面纵横比展开为像素圆形的有界闭合路径。主机 MUST 在发送前拒绝非法结构、类型、越界展开点及超过500运动报告的路径，不裁剪、不拆成多个按下动作。新动作 MUST 保持陈旧画面检查、串行执行、取消及独立目标核验，ADB不得伪造支持。
#### Scenario: Model selects a curved stroke
- **WHEN** 已校准且支持path的HID收到合法多个点
- **THEN** 主机映射同一完整截图坐标与计数校准，发送一条包含完整路径的命令，随后独立取图核验
#### Scenario: Drawing is invalid or unavailable
- **WHEN** 旧固件/ADB收到绘图动作，或路径/圆形结构、范围、预算不满足约束
- **THEN** 在设备输入前拒绝，不部分执行、裁剪或自动回退
#### Scenario: Circle is drawn on a tall screen
- **WHEN** 模型选择合法circle
- **THEN** 展开路径的水平/垂直像素半径相同且首尾一致，不将截图比例当成圆的比例
