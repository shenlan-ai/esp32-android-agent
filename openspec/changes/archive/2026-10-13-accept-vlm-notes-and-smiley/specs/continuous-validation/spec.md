## ADDED Requirements

### Requirement: Real visual-model examples have observable evidence
项目 SHALL 提供白板画笑脸与新建备忘录输入hello的可复现起始条件。实际验收 MUST 记录真实模型与控制路线、动作、独立可见结果、失败及未执行项，不得以预置图案、模拟输入或模型完成声明替代手机结果。分段swipe绘图 MUST 明确没有连续曲线能力。

#### Scenario: A configured model attempts the two examples
- **WHEN** 已配对校准的手机使用视觉模型在空白测试内容执行目标
- **THEN** 记录实际新内容及完整目标是否达到，不能修改既有笔记或把失败标为通过

#### Scenario: Native drawing is unavailable
- **WHEN** 手机没有可用绘图入口或不接受鼠标绘图
- **THEN** 可使用显式离线测试页并标注其条件，不宣称原生App验收通过
