# project-governance Specification

## Purpose
为本项目的代码、固件、配置、文档和开发工具修改建立统一可追溯的规格驱动流程，保证贡献者能够了解变更动机、行为约定、实施范围和实际验证结果。

## Requirements

### Requirement: Every change is tracked before implementation
贡献者 MUST 在修改项目文件前创建或更新对应 OpenSpec 变更，完成 proposal、必要规格、design、tasks 和文件范围清单。纯文档或内部重构 SHALL 显式声明不改变产品行为。

#### Scenario: A feature is implemented
- **WHEN** 贡献者开始实现新的手机控制能力
- **THEN** 对应变更已有规格场景、设计、待执行任务和文件范围，且严格校验通过

#### Scenario: A documentation correction is implemented
- **WHEN** 修改不改变产品行为的安装说明
- **THEN** 变更明确设置 skip_specs 并记录说明、任务、文件范围和验证方式

### Requirement: Changed files have traceable scope
项目 SHALL 提供检查入口，检测待提交修改是否被当前变更或本次新归档变更的 files.txt 覆盖，并对缺少覆盖的文件返回非零退出码。

#### Scenario: Untracked implementation file is added
- **WHEN** 新增实现文件没有对应范围声明
- **THEN** 范围检查失败并列出文件路径

#### Scenario: A completed change is archived
- **WHEN** 本次修改包含新归档变更及其实现文件
- **THEN** 检查可使用该新归档变更的范围声明，但不使用既有历史变更替未来修改授权

### Requirement: Validation reflects actual evidence
贡献者 MUST 记录实际执行的检查、结果和未执行的验收，并只勾选已完成任务。归档 SHALL 在任务完成、规格通过和验证记录存在后进行。

#### Scenario: No physical device is available
- **WHEN** 软件测试通过但手机与板子未连接
- **THEN** 记录明确区分模拟测试、编译检查和未执行的实机验收，不声明硬件已验证

### Requirement: Standard agent instructions have one source
项目 SHALL 通过 AGENTS.md 提供自动读取的开发规则，并通过 agent.md 链接同一规范，避免两份冲突的规则。

#### Scenario: A contributor reads agent.md
- **WHEN** 贡献者打开用户指定的规范入口
- **THEN** 可以访问完整规范和 OpenSpec 开发步骤
