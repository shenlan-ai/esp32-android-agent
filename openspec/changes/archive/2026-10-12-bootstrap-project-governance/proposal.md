## Why

项目目前只有参考项目检出和讨论形成的架构文档。用户要求全部更改通过 OpenSpec 管理，需要先建立可执行的规范、规格基线和校验入口，使后续开发可追溯。

## What Changes

- 初始化 OpenSpec，采用 spec-driven 流程，明确 proposal、specs、design、tasks、验证和归档顺序。
- 新增 AGENTS.md 作为自动读取的项目开发规范，agent.md 作为用户请求的入口。
- 将已有整体设计纳入首次变更，保留其设计状态及上游来源，建立产品规格基线。
- 建立 README、贡献指南、许可证声明、忽略规则和规格校验脚本。
- 初始化本项目 Git 仓库；参考检出保持独立，不纳入产品运行和发布。

## Capabilities

### New Capabilities
- `project-governance`: 所有项目修改都必须有 OpenSpec 变更、任务和实际验证记录。
- `product-foundation`: 定义本地运行、ADB 体验模式、ESP32 主模式和分阶段交付的产品边界。

### Modified Capabilities
无。

## Impact

影响项目规范、文档、OpenSpec 元数据和源码仓库初始化，不引入手机操作行为。已存在的架构文档纳入本变更记录，后续修改必须先有对应规格。
