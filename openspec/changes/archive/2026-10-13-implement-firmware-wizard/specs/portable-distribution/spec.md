## ADDED Requirements
### Requirement: Separate firmware tool and corresponding sources
Windows便携包 SHALL 包含独立固件工具和其许可、实际依赖版本与对应源码；应用进程 MUST 不导入esptool。源码安装 SHALL 将firmware依赖作为可选extra，缺少工具仍可使用工作台。解压验收 MUST 执行独立工具无设备diagnose并验证网页固件入口，无需系统Python或Arduino。

#### Scenario: Portable user has no development environment
- **WHEN** 用户解压程序且系统没有Python或Arduino
- **THEN** 独立固件工具可运行，页面显示四板catalog，写入仍需完整备份与明确确认
