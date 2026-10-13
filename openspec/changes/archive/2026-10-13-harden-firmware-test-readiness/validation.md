实现前strict通过。Python3.12首次完整回归复现PID文件空内容，其他215测试通过、1跳过；Python3.10为216通过、1跳过。

修改后Python3.12完整回归216 passed、1 skipped、1依赖弃用警告，实际超时与取消均通过。Python3.10真实子进程定向测试2 passed、26 deselected；完整回归已在本修正前通过。server目录Ruff通过。等待完整PID并在finally回收任务，不改变产品行为、未增加依赖。Windows跳过为既有symlink权限检查；Linux/远程CI未执行。

`openspec validate --all --strict --no-interactive`：18项通过；`python scripts/check_changes.py`：52修改文件范围通过；`git diff --check`通过（仅Windows换行提示）。全部任务完成，归档本测试修正；手机验收与BLE诊断变更继续活动，不能混称完成。
