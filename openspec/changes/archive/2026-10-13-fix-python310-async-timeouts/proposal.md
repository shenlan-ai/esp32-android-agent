## Why

在独立Windows/Python3.10.21环境运行现有集成测试，任务活动时限被报告为Unexpected task error，BLE动作超时测试失败。源码审计发现四个模块捕获内建TimeoutError；Python3.10的asyncio.TimeoutError与它不同，3.11+才成为别名。相同遗漏还影响USB drain/close/auth超时和SSE心跳，违反已声明的Python>=3.10行为。

## What Changes

- 在agent、BLE、USB及SSE的asyncio.wait_for边界捕获asyncio.TimeoutError，保持3.11+原行为。
- 保持未知输入不重放、超时连接失效与任务释放原因；USB写/关闭/认证超时正确收口，SSE空闲心跳后继续订阅。
- 添加实际wait_for超时测试，证明USB发送不重放、关闭有界、认证超时无未处理异常、SSE心跳后事件仍可交付；复用已有Agent/BLE/USB场景。
- 在Windows/Python3.10和3.12分别运行相关与完整回归；不改变固件或模型接口，不触物理串口。

## Capabilities

### Modified Capabilities
- `agent-execution`: 活动时限在支持版本均正确结束与释放。
- `ble-serial-control`: 串口动作超时在3.10也报告未知并失效，不重放。
- `usb-hid-control`: 支持版本均处理网络发送、关闭和认证的异步超时。
- `task-history`: 空闲SSE心跳不结束支持版本的事件订阅。

## Impact

只修改四个Python模块、新超时场景测试及对应正式规格。独立文档变更complete-open-source-onboarding保持活动，待3.10验证完成；旧归档不改。现有8890仍运行3.12版本，修复验证后择空闲更新，板上程序和原Flash保持不动。

## Extended scope before implementation

完整3.10回归停在USB心跳取消；独立localhost复现显示心跳cancel后仍在循环。Python3.10/3.11的wait_for存在完成与外层取消竞态。统一应用内有时限的异步等待为基于asyncio.wait的可取消包装，明确超时后回收子任务；同时覆盖ADB与固件工具只读操作的取消边界。固件写入仍由原拥有任务保护，不改变覆盖确认、关闭等待或设备操作。新增确定性的完成/取消竞争和超时回收场景。
