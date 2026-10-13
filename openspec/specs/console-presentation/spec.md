# console-presentation Specification

## Purpose
定义本机控制台的视觉层级、功能可达性和响应式交互，让用户优先观察手机并执行任务，保留真实控制能力及安全状态。

## Requirements

### Requirement: Focused workspace and reachable configuration
控制台 SHALL 默认优先展示手机画面与任务工作区，通过具名入口访问设备连接和模型设置。隐藏面板 MUST 保留未保存表单输入和现有后台状态订阅，所有固件、无线、BLE、USB与校准入口 MUST 可达。

#### Scenario: User opens settings and returns to workspace
- **WHEN** 用户在模型设置填写尚未保存的信息并切换工作区后返回
- **THEN** 输入保留，任务和手机状态继续更新，不自动改变设备或控制模式

### Requirement: Persistent safety and honest live status
控制台 MUST 在每个视图提供清晰的紧急停止和状态，保留 Esc 停止以及原有能力、任务、固件、帧坐标限制。空态、断线和错误 MUST 基于真实服务结果展示，不能用静态成功状态替代。

#### Scenario: Capture or connection is unavailable
- **WHEN** 服务或截图不可用
- **THEN** 展示可读错误或连接指引，保留停止入口，不展示伪造就绪状态

### Requirement: Responsive bilingual accessible controls
控制台 SHALL 支持中文/英文和桌面/窄屏布局，具名控件具有可见键盘焦点，内容在390像素宽和200%缩放下 MUST 不重叠或造成页面横向溢出，动效 MUST 尊重 prefers-reduced-motion。

#### Scenario: Keyboard user switches views on a narrow screen
- **WHEN** 用户在窄屏以键盘选择设备或设置入口
- **THEN** 当前入口可辨识，面板标题获得焦点，原控制可达，停止保持可达
