## Purpose

让用户通过本机控制台保存设备与模型配置，在手动模式下无需模型密钥，并通过原子写入、密钥掩码与访问边界避免配置损坏和意外泄露。

## ADDED Requirements

### Requirement: Persistent settings and masked secrets
系统 SHALL 在本机用户配置目录原子保存设置，返回密钥是否存在而不返回密钥内容；未填写新密钥时保留原值，仅显式清除请求才能删除。

#### Scenario: User changes the model name only
- **WHEN** 保存设置且未提供新密钥
- **THEN** 旧密钥保留，API 响应和日志不包含其明文

### Requirement: Local access by default
系统 SHALL 默认仅监听本机，校验访问主机与跨站修改请求；显式远程绑定 MUST 配置访问令牌才能启动。

#### Scenario: A foreign page sends a mutation
- **WHEN** 浏览器从其他源提交控制请求
- **THEN** 服务在调用设备前拒绝

#### Scenario: Remote bind has no token
- **WHEN** 用户指定非本机监听而未配置访问令牌
- **THEN** 启动失败并提供配置说明
