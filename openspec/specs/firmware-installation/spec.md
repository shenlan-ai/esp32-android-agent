# firmware-installation Specification

## Purpose
让用户在本机网页中根据真实硬件证据选择固件、保存完整原Flash，再明确确认覆盖并校验结果；固件写入独立于模型输入及浏览器请求生命周期，并可用无设备模拟检验失败边界。

## Requirements

### Requirement: Evidence-bound firmware selection
向导 MUST 读取真实芯片、MAC与Flash，只列支持且容量/系列匹配的profile，不猜测商品PCB。identify SHALL 不加载stub或写Flash；backup/write MUST 在同一ROM连接校验预期身份并执行，掉线不能自动按端口重放。

#### Scenario: Classic board is identified
- **WHEN** 用户选择4MB经典ESP32的串口并识别
- **THEN** 显示经典BLE profile、芯片/容量及PCB未知，不提供S3固件写入

#### Scenario: Board was replaced on the same port
- **WHEN** backup/write连上板子的MAC、系列或容量与已确认身份不同
- **THEN** 在Flash写入前拒绝操作并要求重新识别

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

### Requirement: Honest write result and local recovery evidence
工具 SHALL 使用已验证的内存镜像执行写入与读取校验，报告镜像校验和手机输入验收为不同证据。失败 MUST 保留完整原备份并说明可能未知的写入结果，不暴露任意路径、原始Flash内容或密钥到日志。历史备份 SHALL 不在服务重启后自动恢复写入。

#### Scenario: Writing succeeds but phone input has not been tested
- **WHEN** 四个镜像写入并读取校验通过
- **THEN** 报告固件镜像通过，提示继续BLE配对或S3配网/手机验收，不声称全机型输入兼容
