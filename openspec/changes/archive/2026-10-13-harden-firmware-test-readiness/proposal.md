## Why
真实子进程取消测试仅等待PID文件存在，文件创建到写入之间的竞态会读取空字符串。Python3.12完整回归已复现，早期断言也应清理测试拥有的进程。

## What Changes
有界等待完整正整数PID，测试拥有的任务在finally取消并回收。保持实际父子进程超时/取消和树清理检查，不修改产品行为，因此无需规格delta。

## Capabilities
无产品行为变更，skip_specs: true。

## Impact
仅server/tests/test_firmware.py及本变更元数据。
