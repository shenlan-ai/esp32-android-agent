## ADDED Requirements
### Requirement: Capability-scoped action examples
动作模型收到的输入示例 SHALL 仅包含当前控制器声明的动作，导航名称必须为独立合法JSON，不得包含伪动作home|back|recents。done/fail/replan元决策 SHALL 始终可用，提示 MUST 明确禁止元决策携带输入字段。示例筛选 MUST 不替代严格解析、真实执行能力门禁、预算和独立目标核验；不支持动作不得自动转换或重放。
#### Scenario: HID cannot issue Android navigation keys
- **WHEN** 当前HID未声明home/back/recents
- **THEN** 动作提示不提供这些输入示例，仍提供元决策与当前声明的输入示例
#### Scenario: Input is unavailable or calibration is missing
- **WHEN** 当前控制器仅有键盘能力或没有输入能力
- **THEN** 仅列实际可用输入示例并继续提供元决策，模型done仍需独立目标核验
