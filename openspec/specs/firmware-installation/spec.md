# firmware-installation Specification

## Purpose
让用户在本机网页中根据真实硬件证据选择固件、保存完整原Flash，再明确确认覆盖并校验结果；固件写入独立于模型输入及浏览器请求生命周期，并可用无设备模拟检验失败边界。

## Requirements

### Requirement: Evidence-bound firmware selection
向导 MUST 在同一ROM连接初始化实际SPI Flash接口后读取真实芯片、MAC与Flash，只列支持且容量/系列匹配的profile，不猜测商品PCB或默认容量。identify SHALL 不加载stub、不擦除或编程Flash；初始化或容量检测失败 MUST 保持拒绝。backup/write MUST 在同一ROM连接校验预期身份并执行，掉线不能自动按端口重放。

直接API连接 MUST 在读取前设置有限串口读取超时；stub握手失败 MUST 关闭当前连接、不自动重试、不开放完成备份或开始Flash写入。

#### Scenario: Classic board is identified
- **WHEN** 用户选择4MB经典ESP32的串口并识别
- **THEN** 初始化该ROM的实际Flash接口后读取真实容量，显示经典BLE profile、芯片/容量及PCB未知，不提供S3固件写入

#### Scenario: Board was replaced on the same port
- **WHEN** backup/write连上板子的MAC、系列或容量与已确认身份不同
- **THEN** 在Flash写入前拒绝操作并要求重新识别

#### Scenario: ROM flash interface is not initialized or fails
- **WHEN** 直接工具API新连接尚未初始化Flash，或初始化失败
- **THEN** 正常流程先在同一ROM初始化再读取；失败不猜容量、不加载stub识别或开始Flash写入

#### Scenario: Stub startup receives no response
- **WHEN** 同一连接身份已核对但临时stub未完成握手
- **THEN** 有限读取超时终止本次操作并关闭连接，不重新连接、不生成完成备份或开始Flash写入

### Requirement: Complete backup and explicit single-use overwrite confirmation
每次覆盖前 MUST 完整备份Flash并记录SHA256，原子标记完成，允许授权下载。写入 MUST 需要StrictBool明确确认与300秒内一次性ticket，绑定设备、profile、备份和暂存镜像；失败、过期、错误或已用ticket不得写入。损坏/不完整备份和镜像 MUST 在写前拒绝。

#### Scenario: Backup is incomplete
- **WHEN** 备份工具成功退出但文件长度不等于真实Flash
- **THEN** 不开放写入确认或下载该备份

#### Scenario: User confirms the prepared firmware
- **WHEN** 备份与镜像有效且用户提交正确未使用ticket和true确认
- **THEN** 复核身份和完整性后写入并读取校验，ticket消耗且重复请求不重放

### Requirement: Owned firmware job and exclusive device maintenance
固件job SHALL 由应用拥有的后台任务执行，与HID/ADB输入、任务启动/恢复、选择设备、控制绑定及串口配网互斥；网页断开/刷新和手机紧急停止 MUST 不取消写Flash。只读识别/备份可取消，写入/校验取消 SHALL 拒绝。优雅关闭 MUST 等待拥有的操作完成，超时或失败不得自动重试。

#### Scenario: Browser disconnects during writing
- **WHEN** 已授权写入的HTTP请求或网页关闭
- **THEN** 后台写入/校验继续，GET可重新获取阶段和结果

#### Scenario: Phone stop during firmware writing
- **WHEN** 用户按Esc或手机紧急停止
- **THEN** 释放手机输入但不终止固件工具，也不排队在刷写结束后执行旧动作

#### Scenario: Read-only operation completes while cancellation arrives
- **WHEN** 支持Python版本中只读操作完成与显式取消同时到达
- **THEN** 系统 MUST 保留取消并回收相关等待或子进程，写Flash仍由原拥有任务规则保护

### Requirement: Honest write result and local recovery evidence
工具 SHALL 使用已验证的内存镜像执行写入与读取校验，报告镜像校验和手机输入验收为不同证据。失败 MUST 保留完整原备份并说明可能未知的写入结果，不暴露任意路径、原始Flash内容或密钥到日志。历史备份 SHALL 不在服务重启后自动恢复写入。

#### Scenario: Writing succeeds but phone input has not been tested
- **WHEN** 四个镜像写入并读取校验通过
- **THEN** 报告固件镜像通过，提示继续BLE配对或S3配网/手机验收，不声称全机型输入兼容

### Requirement: Sanitized stage-aware firmware failures
工具失败 SHALL 仅报告固定操作/阶段/类别和有界已完成读取计数，不传递异常原文、身份、路径、Flash内容或密钥。主机 MUST 严格验证失败信封、枚举及整数边界，使用自有固定提示；只读失败/超时/非法回复 SHALL 明确无Flash写入，write写入/校验或未知阶段失败 SHALL 保留结果不确定的提示与完整备份。诊断 MUST 不放宽确认、完整性或引入自动重读/重写。

#### Scenario: A later backup range fails
- **WHEN** 官方读取在某后续范围失败
- **THEN** 失败信封记录read阶段及此前完整成功的字节数，不把失败范围计为完成，不重试，主机提示备份失败且无Flash写入，不开放确认

#### Scenario: Failure diagnostics are invalid or from an older tool
- **WHEN** 工具非零退出但信封缺失、类型错误、操作不匹配、计数越界或输出超长
- **THEN** 主机使用当前操作的通用提示，不回显外部字段、stderr或异常原文，仍回收进程且不重试

#### Scenario: Flash verification fails
- **WHEN** 已授权写入后的校验失败
- **THEN** 诊断只给出固定校验阶段/失败类别，明确镜像未验证且保留备份，不声称未写Flash或自动再次写入
