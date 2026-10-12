## Why

用户已经能通过网页配网和控制手机，但安装固件仍需要Python命令及单独的esptool，而且现有刷写CLI只支持经典4MB ESP32。开源用户需要便携包内直接完成识别、完整备份、明确覆盖确认和写后校验，避免依赖Arduino环境和猜测商品板型。

## What Changes

- 网页增加识别→选择匹配固件→完整备份→确认写入流程，支持当前经典ESP32 4MB和已编译的三种S3 profile。
- 复用统一芯片/Flash解析与镜像布局验证；用同一ROM连接检查MAC、芯片、Flash并读/写，拒绝设备替换和篡改镜像。
- 所有写入前完整备份到用户data目录，记录SHA256并允许下载；用户确认使用单次、限时、绑定设备/profile/备份/镜像的ticket。
- 后台任务有自己的生命周期；HTTP断开、网页刷新及手机紧急停止不取消写Flash。固件操作期间拒绝设备输入、任务启动/恢复、切换与配网，错误不自动重放或降级。
- 单独子进程工具使用固定esptool5.3.0；Windows便携包提供独立GPL工具、许可及对应源码，应用不在进程内导入esptool。源码通过server[firmware]安装可选依赖。
- 完成真实worker模拟/HTTP并发测试、离线浏览器验收和便携包重建；不再次刷写COM5，不对不存在的S3实物声明输入验证。

## Capabilities

### New Capabilities
- `firmware-installation`: 通过网页识别、备份、显式确认、写入及读取校验。

### Modified Capabilities
- `portable-distribution`: 便携包提供独立固件工具及GPL来源/许可，解压验收覆盖其启动。
- `board-identification`: 识别证据含硬件MAC和容量，保持商品PCB未知并只列匹配已支持profile。

## Impact

服务端固件管理、配置入口、session互斥、轻量网页、共享识别/产物验证、独立工具、打包、测试、CI安装extra及说明。读写工具限定操作，不对模型开放固件能力。不改变HID协议或Android输入。旧归档、参考检出和原Flash备份保持不动。
