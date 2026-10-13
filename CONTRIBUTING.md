# 贡献指南

先阅读 [AGENTS.md](AGENTS.md) 和 [开发流程](docs/DEVELOPMENT.md)。功能、修复、文档、配置和依赖修改都必须关联 OpenSpec 变更。

Issue 描述目标、复现步骤、预期与实际行为，并提供脱敏的系统和设备信息。不要上传 API Key、Wi-Fi 密码或私人截图。

提交或 PR 包含变更 ID、最终修改行为、实际验证命令、未执行验收和兼容性限制。可以使用模拟设备开发，不要求贡献者拥有板子或付费模型。

保持修复范围集中；新能力先约定可观察行为，再写实现。保留上游许可证，避免将参考检出或生成产物提交。

默认英文入口为 [README.md](README.md) 与 [使用说明](docs/USAGE.en.md)，中文入口为 [README.zh-CN.md](README.zh-CN.md)。可用 [离线示例](docs/EXAMPLES.md) 开发完整闭环；实机贡献使用 [验收模板](docs/ACCEPTANCE.md)，按模式和实际设备记录成功/失败/未知、样本与耗时。分享前脱敏；不要用DEMO或模型completed替代人工验证，不要求贡献者购买全部机型。

PR自动检查OpenSpec范围、Linux/Windows Python、网页坐标与四板固件编译；不要求手机和模型账号。可以按开发文档在本机复现。2026-10-13 首次公开源码提交 `0097e23` 的 [GitHub CI](https://github.com/shenlan-ai/esp32-android-agent/actions/runs/38384089654) 在公开后重试通过，10 个 job 成功，四组 Python 各 300 测试通过。便携包另有手动构建工作流，解压验收通过后只提供短期 artifact，不自动发布 Release，尚未远程运行；模拟、编译和 CI 通过也不代表真实手机已验收。
