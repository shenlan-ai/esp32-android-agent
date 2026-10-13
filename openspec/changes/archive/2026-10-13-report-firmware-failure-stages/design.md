## Decisions
perform可选诊断字典，仅由内部代码更新validated/connecting/identifying/stub/read/save/write/verify阶段，不改变现有异常类型和控制路径。开始每个读取范围前记录已完成字节数及总容量；成功段才能增加计数，失败段不重读。main捕获异常时输出operation和failure对象。类别只允许固定映射：packet_transfer_stopped、digest_mismatch、timeout、io_error、operation_failed；匹配异常文本只决定枚举，文本不输出。

主机只在非零退出且stdout未超长时尝试解析失败信封。要求protocol匹配、ok严格false、error和operation匹配，仅接受固定阶段/类别；读取计数必须严格int、0<=completed<total且total为支持容量。额外字段忽略，不拼接外部字符串。diagnose/identify/backup的失败/超时/非法回复都明确无Flash写入；write失败仍保留未知写入结果。备份提示可包含自有阶段名称和整数进度。旧协议保持可用，未知失败不能开放确认。

## Validation
Fake ROM运行真实perform，验证后续段失败的准确进度/stub失败/写校验阶段且无重试；真实main输出检查脱敏。真实子进程测试主机消费有效/非法/伪造/缺失/超长失败信封，超时仍回收进程，两Python版本验证。Ruff、OpenSpec严格/范围检查。此变更不以软件诊断证明USB或BLE实机恢复，现场备份仍待新连接条件复验。

新诊断通过软件和真实身份拒绝流程后，显式启动一次新的生产只读完整备份，用新的阶段/计数观察此前缺失的真实故障细节，不改变串口条件或假称线材修复。该job失败后停止，不自动再次启动；完整成功则交由既有备份下载/确认规范处理，不能因此自动写Flash。
