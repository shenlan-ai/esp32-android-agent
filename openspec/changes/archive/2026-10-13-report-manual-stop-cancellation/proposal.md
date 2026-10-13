## Why

真实Redmi Note14的BLE长按和拖动已经在停止后释放，但停止直接取消FastAPI动作请求任务，CancelledError越过HTTP边界导致动作请求500。网页因此显示服务故障而不能正确解释人工停止，需要区分明确停止与普通请求取消。

## What Changes

- 手动execute/locate在本次session停止epoch变化时，将取消转换为既有可公开DeviceError，HTTP409提示已取消、先观察手机；其他取消和Agent执行继续传播CancelledError。
- 保持串行锁、stop释放确认、未知结果不重放；覆盖并发真实ASGI请求及Agent/外部取消边界。

## Capabilities

### Modified Capabilities
- manual-control: 人工停止对应的动作请求返回可理解的取消结果。

## Impact

session.py、API并发测试与控制测试，不修改固件、动作参数或释放证明。实机重复停止仅在安全本机fixture执行。
