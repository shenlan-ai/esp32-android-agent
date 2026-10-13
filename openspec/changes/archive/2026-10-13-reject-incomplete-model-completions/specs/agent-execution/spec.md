## ADDED Requirements

### Requirement: Incomplete completions cannot issue input
模型客户端 SHALL 拒绝供应商明确声明的截断、过滤、工具调用、拒答及其他非正常或非法结束字段，即使正文恰好是合法动作JSON。拒绝原因 MUST 为固定脱敏提示，MUST 不解析推理/工具字段为动作、不自动重试HTTP或提高预算。正常stop和结束字段缺失/null的旧兼容响应 SHALL 继续严格JSON/能力校验。已完整收到的拒绝completion SHALL 保留真实供应商用量；缺失用量 SHALL 明确估算，但不计为网络结果未知。恢复 MUST 受既有失败及总Token预算约束并保持结束释放。

#### Scenario: Truncated response contains a valid action
- **WHEN** 模型返回finish_reason=length但正文是完整合法tap JSON
- **THEN** 设备收到零输入，任务记录固定额度提示与实际用量，并在既有预算内恢复或终止

#### Scenario: A filtered or tool completion returns content
- **WHEN** 供应商返回过滤/工具/拒答或非法结束信号
- **THEN** 不执行正文，不回显供应商文字、秘密或工具参数，保留已返回用量

#### Scenario: A legacy provider omits termination metadata
- **WHEN** 结束字段缺失或null且没有工具或拒答信号
- **THEN** 仍按严格JSON/参数/能力及独立目标核验处理，不能将兼容性等同真实任务成功

#### Scenario: Rejected completions consume the remaining budget
- **WHEN** 拒绝响应的真实或明确估算用量达到任务总Token上限
- **THEN** 后续模型请求不再发送，任务结束并释放输入，不将已知用量改成网络未知
