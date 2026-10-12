# continuous-validation Specification

## Purpose
为开源贡献者提供无硬件、无付费服务的自动检查和可手动构建验收的便携产物，使所有修改的规格来源与关键行为在贡献流程中可检查，并清楚区分本地、远程CI和实机证据。

## Requirements

### Requirement: Device-free continuous checks
CI SHALL 在Ubuntu和Windows执行Python关键测试，并执行网页坐标和四种固件编译；真实共享固件调度检查 MUST 在已安装依赖的环境执行，不得用缺失依赖的skip代替。流程 SHALL 使用只读仓库权限和固定Actions commit，不读取设备、密钥或调用付费服务。

#### Scenario: A contributor opens a pull request
- **WHEN** GitHub运行PR检查
- **THEN** 执行Linux/Windows的Python检查、网页坐标及四板固件构建，不需要真实手机和模型账号

### Requirement: OpenSpec governance compares the correct baseline
CI MUST 严格校验正式和归档规格，并检查相对于PR base或push before的修改范围；首次push SHALL 使用空树，手动运行 SHALL 使用HEAD。基准不存在或格式非法 MUST 失败，不静默退回HEAD漏检。

#### Scenario: First push has a zero before SHA
- **WHEN** push before为全零SHA
- **THEN** 使用真实Git空树检查全部首次提交内容

#### Scenario: Pull request changes an existing archived record
- **WHEN** 相对PR base修改已归档历史
- **THEN** 范围检查拒绝该修改

### Requirement: Portable artifacts require extracted-process checks
手动Windows产物工作流 MUST 先编译四板、构建便携包、解压并运行真实exe smoke，通过后仅保留ZIP和SHA产物。流程 SHALL 不发布GitHub Release；文档 MUST 区分配置的本地验证与远程首次执行证据。

#### Scenario: Extracted executable fails smoke
- **WHEN** 便携程序缺资源或端口冲突行为错误
- **THEN** 工作流失败且不上传成功产物
