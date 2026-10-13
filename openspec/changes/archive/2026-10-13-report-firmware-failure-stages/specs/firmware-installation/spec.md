## ADDED Requirements

### Requirement: Sanitized stage-aware firmware failures
工具失败 SHALL 仅报告固定操作/阶段/类别和有界已完成读取计数，不传递异常原文、身份、路径、Flash内容或密钥。主机 MUST 严格验证失败信封、枚举及整数边界，使用自有固定提示；只读失败/超时/非法回复 SHALL 明确无Flash写入，write写入/校验或未知阶段失败 SHALL 保留结果不确定的提示与完整备份。诊断 MUST 不放宽确认、完整性或引入自动重读/重写。

#### Scenario: A later backup range fails
- **WHEN** 官方读取在某后续范围失败
- **THEN** 失败信封记录read阶段及此前完整成功的字节数，不把失败范围计为完成，不重试，主机提示备份失败且无Flash写入，不开放确认

#### Scenario: Failure diagnostics are invalid or from an older tool
- **WHEN** 工具非零退出但信封缺失、类型错误、操作不匹配、计数越界或输出超长
- **THEN** 主机使用当前操作的通用提示，不回显外部字段、stderr或异常原文，仍回收进程且不重试

#### Scenario: Flash verification fails
- **WHEN** 已授权写入后的校验失败
- **THEN** 诊断只给出固定校验阶段/失败类别，明确镜像未验证且保留备份，不声称未写Flash或自动再次写入
