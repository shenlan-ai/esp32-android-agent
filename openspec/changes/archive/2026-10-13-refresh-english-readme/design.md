## Context
当前 origin/main 与 HEAD 同步；未提交修改包含已完成并归档的 add-mcp-device-tools、describe-mcp-purpose 与 redesign-local-console。用户明确授权提交推送这些最新修改。

## Decisions
- 英文 README.md 为唯一完整英文源，README.en.md 简短指向新入口以兼容外部旧链接；中文独立 README.zh-CN.md，两份导航互通。
- 首页使用当前控制台的离线 DEMO 截图，并清楚标注模拟来源；原有实机图片保留在案例段，旧工作台只作为历史实机证据链接，不暗示新 UI 已验收硬件。
- MCP 最短步骤从启动并配置已有工作台开始，给出可复制的 Windows/Unix 绝对 Python 路径注册命令、四工具和观察/执行/核验规则；不暴露令牌，不改变用户 Codex 配置。
- 保留现有 Android/板型/输入法/便携包与失败边界，不以测试数量或截图声明全机型兼容。
- 更新 CONTRIBUTING、DEVELOPMENT、USAGE 的语言入口，便携 SOURCE_FILES 增加新中文 README；不重建便携产物。
- 复用最新完整回归证据，另执行文档链接/语言/CLI/源码归档清单及适用工具测试、OpenSpec与范围检查、提交前脱敏检查。推送普通 fast-forward，不强推；推送后核对远端 SHA 与 CI 状态。

## Validation
先严格校验变更；检查本地链接和章节锚点、默认英文与中英文对应内容、Python CLI/MCP --help、便携清单测试。验证记录包含实际命令、复用证据和未执行检查。文档改动无需新增镜像实现测试。
