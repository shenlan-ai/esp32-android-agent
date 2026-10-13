## Decisions

在手动execute包装层及locate捕获取消，比较操作开始epoch与当前epoch。仅epoch变化（明确stop/会话失效）时转换DeviceError；execute_agent直接调用_execute保持取消语义。不能全局吞掉CancelledError、返回ok或声称动作未发生。提示要求观察实际画面后再输入。

stop仍先取消当前任务并等待清理，再通过controller.stop读取释放。队列由既有epoch拒绝。API使用既有AgentError409处理，无新的依赖或响应协议。

## Validation

真实ASGI中启动阻塞手势，等待控制器实际开始，再POST stop；动作409、停止200、单次动作、可继续新输入。定位同样验证。会话级Agent与外部取消仍抛CancelledError。Python3.10/3.12回归、Ruff、实机按下后停止事件与HTTP响应、OpenSpec strict和范围检查。
