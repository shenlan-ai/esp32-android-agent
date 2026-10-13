# agent-execution Specification

## Purpose
使用户可以通过自然语言目标操作安卓手机，同时确保模型动作符合设备能力、依据有效画面执行并验证结果，支持预算限制、暂停接管和恢复，不将不确定操作或模型自述视为成功。

## Requirements

### Requirement: Structured capability-aware single-step execution
系统 SHALL 仅接受通过严格参数校验且属于当前控制器能力的模型动作，每次执行一个改变界面的动作；错误输出 MUST 在输入设备前被拒绝并限次恢复。

#### Scenario: Model returns unsupported or malformed action
- **WHEN** 模型返回未知动作、超范围坐标或非法 JSON
- **THEN** 不执行该动作，记录可理解错误并在预算内重新观察或规划

### Requirement: Fresh observation and explicit outcome validation
系统 MUST 在执行前检查决策画面的几何及相关内容是否失效，动作后取得新画面并验证预期结果。模型宣告完成 SHALL 经过独立目标验证。

#### Scenario: Screen changes while model thinks
- **WHEN** 模型返回前目标区域显著变化或旋转
- **THEN** 旧动作不执行，重新观察

#### Scenario: Model says done without reaching the goal
- **WHEN** 独立目标验证未确认目标达到
- **THEN** 任务不标记完成，继续有限恢复或结束失败

### Requirement: Pause takeover and safe resume
系统 SHALL 支持暂停并释放输入，在暂停后允许手动操作；继续时重新观察与规划。运行中 MUST 拒绝并发手动输入和设备切换。

#### Scenario: User takes over during a model request
- **WHEN** 用户请求暂停
- **THEN** 请求取消，输入释放，任务保留为暂停状态，继续时不重放旧建议

### Requirement: Bounded execution and uncertain outcome recovery
系统 SHALL 限制动作数量、活动运行时间、连续错误和模型调用数量，统计实际提供的 Token 用量；未知用量 MUST 标记估算。画面或控制断线 SHALL 暂停并要求恢复，不自动重放结果未知的输入。支持的Python3.10及以上版本 MUST 一致处理异步活动时限，取消超时工作、释放输入并保留实际时限原因。

#### Scenario: Device drops after an input
- **WHEN** 命令结果不确定
- **THEN** 任务暂停并记录该状态，恢复后根据新画面决策

#### Scenario: Task exceeds its configured limit
- **WHEN** 超过活动时限、动作上限或用量阈值
- **THEN** 结束任务并释放输入，保留原因与已有记录

#### Scenario: Active deadline expires on Python 3.10
- **WHEN** Python3.10运行的任务因asyncio.wait_for活动时限超时
- **THEN** 结束任务并记录time limit原因，取消工作和释放会话，不报告为未识别的普通错误

#### Scenario: Completion races with caller cancellation
- **WHEN** 支持Python版本中有时限的等待完成与外层取消同时到达
- **THEN** 系统 MUST 保留取消并回收等待任务，不能继续执行循环或阻塞停止

### Requirement: Action vision uses normalized coordinate guides
动作模型 SHALL 接收与完整截图0..1000空间一致的可视坐标引导图及明确的坐标上下文。引导 MUST 保持图像大小与截图映射，MUST 不改原始截图、规划/独立核验图片或HID校准；严格动作参数验证保持。

#### Scenario: Model chooses a visible target
- **WHEN** 动作模型读取当前截图
- **THEN** 能参考归一化坐标尺，选择的参数仍按完整截图映射，而非直接使用缩小图像像素

#### Scenario: Independent verifier inspects the result
- **WHEN** 核验模型对操作前后图片判断结果
- **THEN** 收到未加引导的原图，不将辅助线或标签误判为手机内容

### Requirement: Incomplete completions cannot issue input
模型客户端 SHALL 拒绝供应商明确声明的截断、过滤、工具调用、拒答及其他非正常或非法结束字段，即使正文恰好是合法动作JSON。拒绝原因 MUST 为固定脱敏提示，MUST 不解析推理/工具字段为动作、不自动重试HTTP或提高预算。正常stop和结束字段缺失/null的旧兼容响应 SHALL 继续严格JSON/能力校验。已完整收到的拒绝completion SHALL 保留真实供应商用量；缺失用量 SHALL 明确估算，但不计为网络结果未知。恢复 MUST 受既有失败及总Token预算约束并保持结束释放。

#### Scenario: Truncated response contains a valid action
- **WHEN** 模型返回finish_reason=length但正文是完整合法tap JSON
- **THEN** 设备收到零输入，任务记录固定额度提示与实际用量，并在既有预算内恢复或终止

#### Scenario: A filtered or tool completion returns content
- **WHEN** 供应商返回过滤/工具/拒答或非法结束信号
- **THEN** 不执行正文，不回显供应商文字、秘密或工具参数，保留已返回用量

#### Scenario: A legacy provider omits termination metadata
- **WHEN** 结束字段缺失或null且没有工具或拒答信号
- **THEN** 仍按严格JSON/参数/能力及独立目标核验处理，不能将兼容性等同真实任务成功

#### Scenario: Rejected completions consume the remaining budget
- **WHEN** 拒绝响应的真实或明确估算用量达到任务总Token上限
- **THEN** 后续模型请求不再发送，任务结束并释放输入，不将已知用量改成网络未知

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

### Requirement: Capability-scoped action examples
动作模型收到的输入示例 SHALL 仅包含当前控制器声明的动作，导航名称必须为独立合法JSON，不得包含伪动作home|back|recents。done/fail/replan元决策 SHALL 始终可用，提示 MUST 明确禁止元决策携带输入字段。示例筛选 MUST 不替代严格解析、真实执行能力门禁、预算和独立目标核验；不支持动作不得自动转换或重放。
#### Scenario: HID cannot issue Android navigation keys
- **WHEN** 当前HID未声明home/back/recents
- **THEN** 动作提示不提供这些输入示例，仍提供元决策与当前声明的输入示例
#### Scenario: Input is unavailable or calibration is missing
- **WHEN** 当前控制器仅有键盘能力或没有输入能力
- **THEN** 仅列实际可用输入示例并继续提供元决策，模型done仍需独立目标核验
