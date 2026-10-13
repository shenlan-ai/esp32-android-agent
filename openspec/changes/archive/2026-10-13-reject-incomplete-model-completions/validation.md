# 验证记录

已读取正式agent-execution/local-settings、当前客户端/TaskRunner及实机失败报告；客户端确实未检查finish_reason。活动preserve-hid-motion-vector等待用户新刷写授权，本变更只做独立模型客户端/执行预算修复，未发送外部模型或手机输入。实现前`openspec validate reject-incomplete-model-completions --strict --no-interactive`通过；估算设计补充后再次strict通过才实现。

## 红绿证据

`.venv/Scripts/python.exe -m pytest -q server/tests/test_llm.py::test_truncated_completion_cannot_supply_a_valid_action`：旧实现失败，DID NOT RAISE ModelProtocolError，明确接受了finish_reason=length且合法tap正文；新实现1通过。完善测试第一次53项中1失败，原因是测试预期Token limit与既有Token usage threshold提示不一致；同时Ruff提示测试import排序，已修正测试并重跑通过，不改变产品预算行为。

## 回归

- `.venv/Scripts/python.exe -m pytest -q server/tests/test_llm.py server/tests/test_agent.py`：53通过。真实httpx Mock客户端和TaskRunner联合覆盖零设备输入、三次限次恢复准确993tokens、1110tokens越限后仅两次请求、缺Usage明确估算、关闭客户端/释放任务所有权、无model_usage_unknown；原网络中断/取消unknown语义仍通过。
- `.venv/Scripts/python.exe -m pytest -q server/tests`：Python3.12.14，260通过/1 Windows symlink权限skip/1依赖弃用warning，28.60秒。
- `.runtime-local/python310/venv/Scripts/python.exe -m pytest -q server/tests`：Python3.10.21，260通过/1 Windows symlink权限skip/1依赖弃用warning，28.84秒。
- 全源码Ruff通过；本变更strict通过，`python scripts/check_changes.py`157修改文件范围通过，`git diff --check`通过。

未重跑无修改的网页/固件编译；上一变更四配置构建和57工具测试已通过。无外部付费模型调用、真实手机动作或Flash写入。真实模型结束可靠性及笑脸仍未通过；此修复只拒绝已明确未正常结束的输出并保留用量，不保证供应商成功或像素精度。
