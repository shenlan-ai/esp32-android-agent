## Why

用户需要按已确认方案完整实现安卓版。首先建立不依赖板子和模型的可运行工作台，让设备连接、画面、坐标和手动输入可独立验证，成为后续 Agent 与 ESP32 的基础。

## What Changes

- 新增 Python 服务包、应用生命周期、统一动作和设备会话。
- 支持 ADB 设备列表、USB 选择、无线配对与连接、发现及诊断。
- 按需截图、校验图像、统一坐标和过期几何检查。
- 实现基础手动动作、停止和串行调度。
- 提供本地设置及密钥掩码、轻量响应式中英控制台。
- 建立假 ADB 集成测试与运行说明。

## Capabilities

### New Capabilities
- `device-connection`: 明确选择可用安卓设备并提供无线连接与错误恢复提示。
- `screen-capture`: 获取有效的新截图，处理坐标、方向和过期画面。
- `manual-control`: 校验并串行执行基础动作，支持停止和人工控制。
- `local-settings`: 本机持久配置、密钥掩码和默认本机访问。

### Modified Capabilities
无。

## Impact

影响 server、网页、README、开发命令和测试；使用 Python 3.10+、FastAPI、httpx、Pillow、Pydantic。Agent 自动任务和 ESP32 协议由后续变更实现，本变更不将其显示为可用。
