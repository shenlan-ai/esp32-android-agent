## ADDED Requirements

### Requirement: Conservative bounded backup transfer
向导及传统经典刷写脚本的完整固件备份 SHALL 保持初始115200波特率；向导 SHALL 在同一连接核对实际身份并完整读取，主机期限 SHALL 为max(600秒, Flash字节数/8192+60秒)。失败 MUST 不自动切速、重连或重试，仍拒绝覆盖。低速备份 MUST 不放宽完整长度、SHA256、下载及写入确认规则。

#### Scenario: High-speed transport is unreliable
- **WHEN** 用户启动新的完整备份
- **THEN** 工具不提升备份传输速率，完成实际长度和散列核验后才开放确认；传输失败保持失败，不自动重试

#### Scenario: Larger supported Flash is backed up
- **WHEN** 已识别8MB支持的芯片执行低速完整读取
- **THEN** 容量匹配期限超过600秒且仍有界，不能因沿用4MB期限提前截断

#### Scenario: Classic board is backed up through the legacy script
- **WHEN** 用户运行传统经典4MB刷写脚本的备份或明确确认后的刷写流程
- **THEN** 完整备份也使用115200及600秒，校验长度和SHA；失败不执行write，成功后的write保持460800及180秒

#### Scenario: Prepared firmware is written
- **WHEN** 用户明确确认有效备份与一次性ticket
- **THEN** 写入仍使用现有460800速率与读取校验，备份速率修改不引入失败重写

#### Scenario: Wizard completes contiguous bounded reads
- **WHEN** 向导在已核验身份的同一连接开始完整读取
- **THEN** 按最多256KB连续无重叠范围读取并保留esptool每段传输摘要检查，检查每段实际长度；所有范围完成后才落盘并核验完整长度/SHA，任何一段失败不得重读、重连或开放写入
