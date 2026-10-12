# product-foundation Specification

## Purpose
定义本地运行的安卓视觉操作项目的产品边界、无硬件体验与 ESP32 主使用路径，以及发布和兼容性声明方式，为后续各能力规格提供共同基线而不声称规划功能已经实现。

## Requirements

### Requirement: Local operation and optional model provider
产品 SHALL 在用户电脑上运行服务与控制台，允许手动操作不配置模型，并在自动任务中使用用户选择的 OpenAI 兼容视觉接口。

#### Scenario: Manual setup has no model key
- **WHEN** 用户只验证手机画面和手动操作
- **THEN** 系统不要求提供模型密钥或项目云服务账号

### Requirement: Two explicit control paths
产品 SHALL 提供 ADB 体验路径和 ESP32 HID 主路径，明确展示当前控制方式，并禁止未经用户操作自动切换控制后端。ESP32 主路径 SHALL 使用无线 ADB 获取画面。

#### Scenario: User starts without a board
- **WHEN** 用户选择 ADB 体验路径
- **THEN** 可在无 ESP32 的情况下验证画面、基础控制和模型任务

#### Scenario: Hardware control loses connection
- **WHEN** ESP32 控制连接中断
- **THEN** 系统报告断线并停止当前操作，不自动改用 ADB 执行

### Requirement: Compatibility claims have evidence
产品文档 MUST 区分已验证、待验证和后续能力，并标注板型、机型、Android 版本及验证方式。v0.1 SHALL 以 ADB 和 ESP32 两条路径可用为交付目标。

#### Scenario: An optional capability is planned
- **WHEN** 记录 Unicode、伴侣 App 或绝对坐标 HID 的后续计划
- **THEN** 文档不将该能力表述为当前可用或全机型兼容
