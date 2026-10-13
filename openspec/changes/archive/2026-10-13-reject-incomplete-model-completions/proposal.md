## Why
实机模型曾返回finish_reason=length且正文为空，目前只被归为普通JSON错误。客户端忽略finish_reason，因此截断、过滤或工具调用响应若正文恰好为合法动作JSON，仍可能送到设备；任务也无法区分有真实用量的拒绝响应与网络结果未知。

## What Changes
- 在客户端拒绝明确未正常结束的completion，只有stop或缺失结束字段的旧兼容响应继续接受。
- 截断、过滤、工具调用、拒答及非法结束字段使用固定脱敏原因，不解析其中的动作，不重试HTTP或放宽JSON校验。
- 用携带Usage的completion错误保留已返回的真实Token用量；TaskRunner计入预算，缺失用量仍估算，但不将完整收到的拒绝响应计为网络结果未知。
- 添加真实HTTP Mock与TaskRunner回归，覆盖合法动作JSON却finish=length、空正文、过滤/工具分支、旧供应商及预算终止。

## Capabilities
### Modified Capabilities
- agent-execution: 未正常结束的模型输出禁止成为设备输入，已知消耗计入有限恢复预算。

## Impact
server/android_agent/llm.py、agent.py及对应测试、开发/模型限制文档。无新依赖，不改变配置预算、提供商选择、手机输入或BLE刷写；不宣称此检查会使真实案例成功。
