## Why
新增board-status网页测试仅在本机执行，CI仍只运行坐标测试；独立工具及部分维护脚本未进入完整Ruff检查。远程运行前应确保关键诊断回归实际进入检查命令。

## What Changes
CI显式运行坐标与板子状态两组Node测试，统一静态检查server/scripts/tools/packaging。工作流检查器验证这两项覆盖，并用真实YAML删改测试检查拒绝。利用本机Docker隔离Linux环境执行无硬件回归，记录真实范围，不冒充Ubuntu runner或远程CI。

静态检查显式指定server/pyproject.toml，防止仓库外配置或运行目录改变规则；隔离工具回归安装Git和g++，不以缺依赖的skip代替执行。

## Capabilities
### Modified Capabilities
- continuous-validation: 新诊断测试与完整源码静态检查进入持续验证。

## Impact
CI YAML、工作流检查器与其测试、开发说明及兼容性证据。没有产品依赖/行为变化、设备操作或远程发布。
