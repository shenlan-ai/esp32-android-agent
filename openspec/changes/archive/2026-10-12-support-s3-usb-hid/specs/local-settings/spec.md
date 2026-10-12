## ADDED Requirements

### Requirement: Private USB pairing settings
系统 SHALL 原子保存 USB 监听启用状态、板子身份、配对凭据和独立 USB 校准；公开设置仅报告凭据是否存在。配网写入使用受保护修改接口，不向浏览器返回密钥。

#### Scenario: Read public settings after provisioning
- **WHEN** 浏览器请求设置或板子状态
- **THEN** 只返回已配对板子身份和是否有密钥，Wi-Fi 密码与配对密钥不出现在响应中
