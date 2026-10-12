# Validation

2026-10-13，Windows x64。独立Python3.10.21与项目Python3.12.14，未打开COM5，未更改固件或调用手机/外部模型。

- 修复前：3.10 Agent时间预算报告Unexpected task error、BLE超时漏捕。完整回归停在USB心跳取消；本机真实TCP独立复现cancel后心跳仍在sleep循环，证据.runtime-local/python310/reproduce-heartbeat.py及原日志。核对测试PID后仅终止挂起的测试进程。
- 扩展OpenSpec并strict通过后添加async_utils有时限等待：保留外层取消、取消/回收子任务，6模块共享。旧3.10 wait_for取消竞态不再进入生产等待。超时捕获统一为asyncio.TimeoutError。
- Windows3.10：pytest -q server/tests为166 passed、1 skipped、1 warning；9.30s。3.12为166 passed、1 skipped、1 warning；9.21s。日志.runtime-local/python310/pytest-final310.log与pytest-final312.log。随后将清理测试参数化，两解释器新文件均8 passed；覆盖USB发送/关闭/认证、SSE、完成/取消竞态、超时与取消清理、正常结果/异常。
- Ruff在两个环境全server通过；Node几何3 passed。脚本unittest此前3.10实际41 passed，工具/固件未修改。
- skip为Windows文件symlink权限；3.10新Starlette/httpx弃用warning、3.12旧anyio别名warning，未影响结果。未为消除warning更改运行依赖。
- python scripts/check_changes.py范围通过，git diff --check通过；归档前strict及归档后所有规格校验见执行记录。

限制：Linux/远程CI、S3与Android手机、真实模型未参与，不声称这些环境已验收。保持固件写入拥有任务规则、物理板及原Flash不动。
