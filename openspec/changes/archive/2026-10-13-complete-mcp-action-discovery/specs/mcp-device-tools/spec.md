## ADDED Requirements

### Requirement: Complete built-in input discovery

MCP SHALL 通过 android_action 提供内置 Agent 的全部12种输入（tap、swipe、path、circle、long_press、scroll、type、key、home、back、recents、wait），并保持同一个 Action 参数校验与控制串行保护。android_status SHALL 返回当前实际可用动作的共享示例、allowed_keys和绘图参数规则；不可用模式、离线、维护或HID未就绪 MUST 不宣称可执行能力。MCP工具schema SHALL 说明完整截图坐标及每种动作参数，path是持续按住的2..20点笔画，circle半径是横向归一化单位且在真实像素里圆形。内置 done/fail/replan MUST 不伪装为设备输入。验证 SHALL 包含真实SDK经过HTTP的全动作集合检查、ADB输入和HID连续笔画转换，不以模拟代替新Codex会话与真实手机验收。

#### Scenario: An external Agent discovers continuous drawing
- **WHEN** 校准有效且HID就绪，Codex读取状态与工具schema
- **THEN** 返回path/circle样例、合法按键和连续笔画/半径说明，可用新观察通过android_action执行，之后需新截图核验

#### Scenario: Controller mode limits remain visible
- **WHEN** 当前模式为ADB、HID未就绪、手机断线或维护中
- **THEN** 示例及按键只反映当前能力，不支持的绘图/导航或所有输入在执行前拒绝

#### Scenario: A built-in action is added later
- **WHEN** 新输入动作被加入共享Action定义
- **THEN** MCP全动作契约测试要求示例及外部发现同步，不允许默默遗漏

#### Scenario: Codex discovers numeric path points
- **WHEN** 外部客户端将MCP公开schema转换为工具参数
- **THEN** 每个点以标准items整数数组且恰好2项表示，外层2..20点；执行拒绝字符串、浮点、布尔或越界坐标
