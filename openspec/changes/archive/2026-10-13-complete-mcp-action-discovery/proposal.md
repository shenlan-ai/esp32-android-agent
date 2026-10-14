# Proposal

## Why

用户要求确保内置 Agent 的输入工具全部通过 MCP 提供，并在新的 Codex 会话通过源码操控真实手机，在笔记里画笑脸。当前 MCP 已复用所有12种 Action，但未发现可用按键，连续笔画/圆形的字段解释及全动作回归不足。

## What Changes

- 保留4个标准 MCP 工具，完整发现内置输入动作与当前控制器支持的按键、动作示例及连续绘图规则；共享内置 Agent 示例定义，避免分叉。
- 增加真实 MCP SDK → HTTP → 控制器的逐动作覆盖及模式/就绪/维护限制回归。
- 用标准嵌套整数数组表示笔画点，修复Codex对prefixItems元组的类型显示兼容性，保留严格执行校验。
- 更新英文/中文入口与 MCP 说明，说明所有输入通过 android_action 调用，done/fail/replan 属于内置编排决策。
- 在本项目本机私有配置注册源码 stdio MCP，创建新的 Codex 桌面会话完成用户授权的新笔记笑脸；保存脱敏验收记录及结果，原始手机图像只存忽略目录。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `mcp-device-tools`: 完整输入能力发现与逐动作验证。

## Impact

models/agent/mcp/mcp_api、MCP测试、README与MCP/实机验收文档、忽略本机Codex项目配置。没有新依赖，不改固件，不扩大设备/模型/历史/刷写接口。仅本次已授权笔记输入可以临时预批准，结束后移除临时策略；不修改全局 Codex 配置。
