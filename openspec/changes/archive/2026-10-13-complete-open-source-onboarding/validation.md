# Validation

2026-10-13，Windows x64。文档变更，不改变产品行为；实现前strict已通过。

- 增加英文README/完整使用、双语示例/真实验收模板，中文/贡献/使用入口互链。CLI --help与collect_firmware --help核对通过，四profile与GPL/MIT说明对照实际实现。相对链接检查：16份文档75个本机目标均存在。
- 隔离Python3.10.21在.runtime-local/python310安装45项开发/固件依赖，独立工具esptool5.3.0 diagnose、source launcher diagnose及工具unittest41项通过。依赖freeze保存在requirements-installed.txt。
- 最低版本原有异步超时/取消失败通过独立fix-python310-async-timeouts先建立并strict，再实现/验证/归档提交66570dc；未藏入本次文档变更。最终完整pytest：Windows3.10为167 passed、1 skipped、1 warning（9.65s）；Windows3.12.14为167 passed、1 skipped、1 warning（9.35s）。两个环境Ruff通过，Node24.21.0几何3 passed。Windows symlink权限skip和依赖弃用warning明确保留。
- 另一干净3.10 core-venv只安装./server，未含pytest/ruff/esptool。真实子进程诊断、静态首页、API、缺ADB409、可选固件工具缺失通过；独立中文data路径，不使用手机/板/模型。证据core-smoke.json。首次验证脚本Windows子进程清理短暂文件占用已修正为只清理本次进程树后重验通过，产品代码未受影响。
- 按文档启动agent_demo.py，3.10真实进程DEMO标记、假phone1及mock Wi-Fi观察任务completed；结束清理该模拟进程。证据onboarding-demo-smoke.json；真实手机/串口/外部模型未使用。
- 新文档stage后用既有source_archive导出.runtime-local/onboarding-source.zip，227个来源文件；四份新文档与async_utils均收录，没有.runtime-local、Flash、私密.env或运行数据。
- git diff --check、python scripts/check_changes.py及OpenSpec strict/所有正式/归档校验通过，归档后独立提交。

限制：仅本机Windows3.10/3.12真实软件证据；macOS/Linux、远程CI、S3实物、Android15/16/17手机和真实模型均未执行。不把模板/模拟/固件校验视为机型输入、真实成功率/费用。8890读取到idle与无手机，未更改该服务或COM5。goal保持active，实机验收尚需真实设备。
