## MODIFIED Requirements

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
