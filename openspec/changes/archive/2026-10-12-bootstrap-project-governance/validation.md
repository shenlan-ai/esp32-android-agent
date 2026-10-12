# Validation

- `openspec validate bootstrap-project-governance --strict --no-interactive`：通过。
- `python -m unittest discover -s scripts/tests`：6 项通过，覆盖未声明文件、新归档、历史清单不可复用、根目录通配符拒绝及未跟踪文件。
- `python scripts/check_changes.py`：首次检查发现 OpenSpec 初始化生成的两个 .gitkeep 未声明，已补入本变更范围；最终检查见本次命令结果。
- 核对 agent.md 指向唯一 AGENTS.md 规范、许可证保留上游版权、参考检出被忽略。
- 本变更仅建立规范和产品约束，不包含运行时或硬件验收。
