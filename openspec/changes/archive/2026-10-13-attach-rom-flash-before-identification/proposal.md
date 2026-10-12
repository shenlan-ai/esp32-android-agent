## Why

实际COM5经典ESP32的独立固件工具识别了芯片和MAC，却返回flash_bytes=null，向导正确拒绝不确定容量的备份/写入。esptool的CLI会先初始化ROM SPI Flash接口，当前直接API调用遗漏attach_flash，模拟ROM未覆盖该前置条件。

## What Changes

- 在同一ROM连接上先调用esptool attach_flash，再检测容量和身份；不加载stub、不写Flash识别设备，不猜测默认4MB。
- 假ROM要求先初始化才能检测，覆盖识别、备份和写入使用同一连接的先后条件；保留断线不重连、完整备份及一次确认。
- 为直接API连接设置esptool默认的有限串口读取超时，避免stub启动等待恢复到pyserial的无限等待；覆盖stub失败时不生成备份、不写Flash和连接关闭。
- 实际只读识别COM5并核对4MB，再执行完整备份以验证实际工具流程；镜像覆盖属于独立确认，不由本变更执行。

## Capabilities

### Modified Capabilities
- firmware-installation: 初始化实际ROM接口后读取身份与容量，保持只读识别和未知容量拒绝。

## Impact

独立GPL固件工具、假ROM生命周期测试及工具验证说明；主应用不引入esptool，不修改手机设置或现有Flash内容。
