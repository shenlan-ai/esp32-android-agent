## Why

项目已有关键协议、模拟任务和四板固件检查，但都依赖开发者手工运行。开源贡献者需要可自动执行、无设备和密钥的验收入口，并在PR中确保所有修改遵循OpenSpec。

## What Changes
- GitHub Actions 对push、pull_request和手动运行执行OpenSpec范围/严格检查、Linux与Windows Python检查、坐标测试及四个固件构建。
- 手动工作流构建Windows便携包，解压后真实exe smoke，通过后保留短期CI产物；不创建GitHub Release、不发布远程版本。
- 补贡献者说明：本地复现、明确无设备模拟限制和工作流首次远程运行仍待验证。

## Capabilities
### New Capabilities
- `continuous-validation`: 无设备自动检查和手动便携构建。
### Modified Capabilities
无。

## Impact
仅CI配置、验证工具和开发文档，不更改运行时控制能力、不再次刷写COM5。仓库没有授权远程push，本次只提交本地配置与验证证据，首次GitHub执行不可声称通过。
