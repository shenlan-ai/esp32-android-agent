## MODIFIED Requirements

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
