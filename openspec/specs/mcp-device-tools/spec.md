# mcp-device-tools Specification

## Purpose
让Codex及其他外部Agent通过可选的本机stdio MCP桥接获取真实安卓截图、读取当前控制能力并执行单步输入与停止。复用工作台唯一设备会话、校准和控制串行保护，通过有界且一次输入的观察凭据拒绝陈旧/重复动作，保留真实客户端与实机验证边界。

## Requirements

### Requirement: Convenient local MCP bridge
系统 SHALL 提供可选安装的 stdio MCP 入口，向标准 MCP 客户端提供 android_status、android_screenshot、android_action 和 android_stop，通过本机 HTTP 复用已运行工作台的唯一 DeviceSession。核心网页安装 MUST 不要求 MCP SDK；桥接 MUST 拒绝非 loopback、含凭据/查询/片段的服务 URL，不跟随重定向、不使用环境 HTTP 代理。截图 SHALL 返回 MCP ImageContent 与尺寸、0..1000完整截图坐标和不含设备秘密的元数据。

#### Scenario: Codex connects to an existing workbench
- **WHEN** 用户在网页选择并配置手机与控制器后启动 stdio MCP
- **THEN** Codex 可列出四个工具、获得真实图像并使用相同控制器，无第二个串口连接

#### Scenario: Core installation has no MCP SDK
- **WHEN** 用户只安装核心包
- **THEN** 网页正常运行，MCP入口报告安装可选 extra 的简明提示

### Requirement: Observed single-use actions
所有 MCP 动作 MUST 提供服务端生成的 observation_id 和合法 Action。凭据 SHALL 最长有效60秒、内存最多8帧，绑定手机、控制器、停止/选择/校准代次及输入修订。执行 MUST 在共用串行锁内重新取图，检查尺寸、方向、年龄、黑屏及相关区域变化；一次已提交输入 MUST 消耗凭据并使此前观察失效。网页预览不能提前逐出有效 MCP 参考帧。非法参数、能力、校准、任务/维护冲突 MUST 在输入前拒绝；不得自动降级、裁剪或重放。

#### Scenario: Concurrent clients act from the same screen
- **WHEN** 多个客户端基于同一输入修订同时提交动作
- **THEN** 至多一次输入执行，其余拒绝并要求重新观察

#### Scenario: Scene changes while Agent thinks
- **WHEN** 相关画面变化、旋转、凭据过期或设备/控制器/校准/停止代次改变
- **THEN** 旧动作零输入，提示重新截图

#### Scenario: Preview refreshes repeatedly
- **WHEN** 网页预览超过12次刷新而MCP凭据仍新鲜且绑定有效
- **THEN** 保留MCP参考图，动作继续严格检查新画面

### Requirement: Shared stop and uncertain outcomes
MCP SHALL 与网页/内部任务共享控制串行和停止；运行中的内部任务或固件维护 MUST 拒绝 MCP 输入。停止 SHALL 取消当前与已排队输入、作废观察并报告真实释放结果。MCP调用取消、控制HTTP超时或断开 SHALL 尽力请求共享停止并要求重新观察；请求 MUST 不自动重试。截图失败/受保护黑屏 SHALL 作废所有MCP观察并尽力停止释放，错误不能冒充成功。工具结果 MUST 区分命令完成和手机目标达成，Agent须另取图核验。

#### Scenario: Long input is cancelled
- **WHEN** MCP客户端取消控制调用或调用android_stop
- **THEN** 共享会话取消操作并尽力释放，旧观察不得继续执行

#### Scenario: Control response is lost
- **WHEN** HTTP结果超时或断开
- **THEN** 桥接不重放，尽力停止并返回结果未知/需重新观察的工具错误

### Requirement: Authentication and evidence
桥接 SHALL 通过环境变量传递可选访问令牌并遵守现有CSRF保护；不向MCP暴露模型设置、密钥、固件备份或完整任务记录。错误 SHALL 固定脱敏，stdout仅用于MCP协议。验证 MUST 包含有意义的SDK客户端/stdio、参数、图像、陈旧帧、竞争和取消测试；真实Codex调用及手机证据与模拟、未验证系统区分记录。

#### Scenario: Service requires authentication
- **WHEN** 工作台配置访问令牌
- **THEN** 正确环境令牌可连接，缺失/错误令牌拒绝且不回显令牌或用户输入

#### Scenario: Codex acceptance is recorded
- **WHEN** 验证新工具
- **THEN** 记录实际Codex版本、工具调用、图像结果与设备边界，不能仅以自写客户端成功声称Codex验收成功

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
