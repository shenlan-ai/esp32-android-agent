## Why
CI添加的dev依赖PyYAML被uvicorn的可选日志配置import发现，最新便携包因此包含非必要开发依赖。工作台使用字典日志配置，入口未提供YAML配置选项，属于构建内容精简而不改变用户行为。
## What Changes
构建时排除yaml可选模块，保持PyYAML用于贡献者workflow检查。重新构建并验收不含PyYAML的干净提交便携包。
## Capabilities
无能力变化，skip_specs:true；正式portable-distribution行为保持相同。
## Impact
仅Windows构建脚本，不改运行入口、CI、固件或旧归档。
