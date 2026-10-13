## Decisions
等待PID文件内容为非空正整数而非只检查存在，限100次、每次10ms。将读取与实际测试等待放在try/finally；无论断言结果都cancel并gather测试拥有的任务，保留真实进程清理能力检查。不增加对生产实现的模拟或依赖。

## Validation
Python3.10/3.12分别运行实际超时和取消测试；Python3.12完整回归复验、Ruff及OpenSpec范围检查。
