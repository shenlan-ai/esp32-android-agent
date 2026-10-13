# MCP device tools

## Why
外部 Agent（包括 Codex）需要直接看到手机截图并使用当前 ESP32/ADB 控制通道。现有网页会话应继续成为唯一设备拥有者，避免第二个进程抢串口或绕过控制保护。

## What Changes
- 可选 Python MCP SDK / stdio 桥接，四个工具：android_status、android_screenshot、android_action、android_stop。
- 服务端保存有界、短期、单次输入的截图凭据；动作前强制刷新、检查相关区域变化和会话绑定。
- 复用严格 Action、控制串行、能力、校准、任务冲突和停止释放；错误和传输超时不重放输入。
- Codex 接入文档、SDK 协议测试、真实 Codex MCP 与可用手机验收记录。

## Capabilities
### New Capabilities
- `mcp-device-tools`: 本机 stdio MCP 手机观察与控制。
### Modified Capabilities
无；现有网页与内部模型任务契约保持。

## Impact
Python 服务会话、专用 HTTP 桥接端点、可选依赖/入口、测试和文档。无固件覆盖、自动输入法切换或新安卓 App；便携 exe 暂使用独立 Python MCP 桥接。
