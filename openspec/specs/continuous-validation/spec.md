# continuous-validation Specification

## Purpose
为开源贡献者提供无硬件、无付费服务的自动检查和可手动构建验收的便携产物，使所有修改的规格来源与关键行为在贡献流程中可检查，并清楚区分本地、远程CI和实机证据。

## Requirements

### Requirement: Device-free continuous checks
CI SHALL 在Ubuntu和Windows执行Python关键测试，并执行网页坐标、板子状态提示和四种固件编译；真实共享固件调度检查 MUST 在已安装依赖的环境执行，不得用缺失依赖的skip代替。Python静态检查 MUST 显式使用server/pyproject.toml并覆盖server、scripts、tools与packaging源码，工作流检查器 SHALL 拒绝缺失网页测试或静态目录覆盖。流程 SHALL 使用只读仓库权限和固定Actions commit，不读取设备、密钥或调用付费服务。

#### Scenario: A contributor opens a pull request
- **WHEN** GitHub运行PR检查
- **THEN** 执行Linux/Windows的Python检查、网页坐标及板子状态测试、全部源码静态检查与四板固件构建，不需要真实手机和模型账号

#### Scenario: New diagnosis tests are removed from CI
- **WHEN** 网页job漏掉板子状态测试，或Python静态检查漏掉独立工具目录
- **THEN** 工作流检查器拒绝配置，其他job或注释中的命令不能冒充缺失覆盖

#### Scenario: Static checks lose the project configuration
- **WHEN** Python静态命令没有显式指定server/pyproject.toml
- **THEN** 工作流检查器拒绝配置，静态规则不能随工作目录或用户外部配置改变

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

### Requirement: Explicit local physical-input test surface
项目 SHALL 提供贡献者显式启动的本机手机输入测试页面，不自动控制手机、不调用模型、不进入默认CI设备流程。页面 MUST 无外部资源与提交型表单，记录有界的真实指针/键盘事件及本地测试值，用于人工与截图交叉核验。

#### Scenario: Contributor prepares a paired phone
- **WHEN** 贡献者启动fixture并通过已授权ADB reverse在手机打开页面
- **THEN** 可在同一实际控制模式检查目标命中、手势、ASCII和停止；报告具体型号、版本、模式与未执行项，不以页面可访问证明输入通过

#### Scenario: Report is too large
- **WHEN** 页面或客户端提交超出大小/事件数量限制的记录
- **THEN** 服务拒绝超大请求并维持有界缓冲，不执行任何手机动作

### Requirement: Real visual-model examples have observable evidence
项目 SHALL 提供白板画笑脸与新建备忘录输入hello的可复现起始条件。实际验收 MUST 记录真实模型与控制路线、动作、独立可见结果、失败及未执行项，不得以预置图案、模拟输入或模型完成声明替代手机结果。分段swipe绘图 MUST 明确没有连续曲线能力。

#### Scenario: A configured model attempts the two examples
- **WHEN** 已配对校准的手机使用视觉模型在空白测试内容执行目标
- **THEN** 记录实际新内容及完整目标是否达到，不能修改既有笔记或把失败标为通过

#### Scenario: Native drawing is unavailable
- **WHEN** 手机没有可用绘图入口或不接受鼠标绘图
- **THEN** 可使用显式离线测试页并标注其条件，不宣称原生App验收通过
