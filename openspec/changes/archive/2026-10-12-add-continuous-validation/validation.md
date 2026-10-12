# 验证记录

2026-10-12，Windows11 x64、Python3.12.14、Node24.21.0、OpenSpec1.13.1、PlatformIO6.1.19。PyYAML6.0.3只加入dev依赖。

- 实现前/后OpenSpec strict与修改范围检查通过；`git diff --check`通过。
- `git ls-remote`核验actions/checkout v4=`11d5960a326750d5838078e36cf38b85af677262`、setup-python v5=`a26af69be951a213d495a4c3e4e4022e16d87065`、setup-node v4=`49933ea5288caeca8642d1e84afbd3f7d6820020`、upload-artifact v4=`ea165f8d65b6e75b540449e92b4886f43607fa02`。workflow固定这些commit，contents:read，无secrets引用。
- 官方actionlint1.7.12 Windows amd64 ZIP SHA256=`6e7241b51e6817ea6a047693d8e6fed13b31819c9a0dd6c5a726e1592d22f6e9`，与官方checksums一致后解压运行。`actionlint.exe .github/workflows/ci.yml .github/workflows/portable.yml`通过（最终加入native依赖检查后重复通过）。不是GitHub远程运行证据。
- `check_workflows.py`通过只读权限、固定Actions SHA、平台/Python/四板矩阵、治理及先smoke后上传的结构检查。
- `test_ci_base.py`5项真实git测试仓库通过：PR/push原基准、首次空树检查全部文件、非法/缺失/未知SHA失败、blob拒绝、基于真实PR base拒绝旧归档修改。`ci_base.py --event workflow_dispatch`返回当前HEAD。
- `pytest -q server/tests`131通过、1跳过、1warning（Windows文件symlink权限及Starlette/anyio弃用）；`unittest discover -s scripts/tests`33通过，实际共享固件g++22场景执行；Node3项通过；Ruff服务端及新增脚本通过。
- 本机四板PlatformIO增量构建均通过：经典1环境SUCCESS、S3三环境SUCCESS。编译工具/框架版本仍为锁定配置；本次未修改固件源代码，未重新刷写COM5。
- 干净提交0f8684b的便携包真实构建后，解压到`dist/最终 便携验收`，真实exe smoke全部通过，移除系统Python/ADB路径，隔离中文data目录，无真实设备或模型调用。ZIP SHA256=`0ba8d12a0af3f28386b10911007da5911c4f99560c85df1517fb73f518711551`；报告`.runtime-local/portable-final-smoke.json`，构建日志`.runtime-local/portable-final-build.log`。这是便携工作流命令的本地等效验证。

未执行：GitHub远程workflow、Ubuntu/Python3.10矩阵与Linux文件symlink测试（本机环境为Windows/Python3.12）；Android/S3/真实供应商模型验收。未push、未上传artifact或创建Release。上述未执行项在开发/贡献文档明确记录，不以本机验证替代。
