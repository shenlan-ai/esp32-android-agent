## 软件与构建

- 实现前`openspec validate diagnose-ble-readiness --strict --no-interactive`通过。
- Python3.12.14：BLE/USB相关85 passed；完整回归216 passed、1 skipped、1既有依赖弃用警告。Python3.10.21完整216 passed、1 skipped、1既有依赖弃用警告。
- 两环境`python -m unittest discover -s scripts/tests`各44测试通过，包含实际共享调度器27场景及真实ArduinoJson诊断序列化7场景。初始无密钥断言误匹配合法key能力名称，改为检查JSON字段后通过。
- `node --test server/tests/board-status.test.mjs server/tests/geometry.test.mjs`：5通过。中英文提示、旧固件、USB、断线优先和诊断全true但权威未就绪均验证。
- 在server目录`python -m ruff check android_agent tests`通过。
- 经典`python -m platformio run -d hardware/ble_bridge`成功；RAM39188/327680、Flash1136673/1966080字节。未改USB/共享调度，沿用三款S3已验证编译产物。
- 新catalog `.runtime-local/firmware-diagnostics-20261013`收集四板并验证镜像；经典0.1.2应用SHA256 `84d0664dcecce24667e08ee6ce499294eea49399ffd2219c93dabd098578b51f`。
- 首次3.12完整回归遇到既有子进程测试PID空文件竞态（215通过、1失败、1跳过）；独立`harden-firmware-test-readiness`先规范再修正，完整复验通过。

## 设备与限制

重新配对后实际COM5仍为0.1.1、串口connected=true、hid_ready=false。未发送定位/点击/输入，没有以手机设置的已连接代替权威就绪。

生产工作台已重启到最新主机实现和0.1.2 catalog；保留手机选择，切ADB只为串口维护，未发送ADB输入。ROM再次识别为ESP32-D0WD-V3 rev3.1、4MB、仅esp32dev兼容，已启动本次完整备份。0.1.2尚未刷入，没有本次覆盖确认；软件测试不证明实机故障原因或手机输入成功。实机任务未完成，保持活动状态。

完整备份两次在460800读取失败，均未生成完成备份或执行Flash写入。串口RTS恢复后hello仍0.1.1；只读诊断确认stub/切速成功，实际read_flash报Packet content transfer stopped。115200整片读取也在386.5秒失败；64KB及末尾256KB低速读取通过。独立变更`use-conservative-firmware-backups`先规范后实现保守速率、容量期限及同连接连续分段，生产向导新分段完整备份仍在193.4秒失败。均未写Flash，失败后重新绑定生产BLE，串口connected=true、firmware=0.1.1、hid_ready=false，没有发送HID输入。建议更换数据线并直连主机USB口排查，尚未确定完整读取失败根因。主机通过HTTP提供新board-status.js/app.js均200；实机分层状态必须待新版刷入，不能由软件检查推断。

用户2026-10-13确认更换线材及直连USB后，新生产完整备份335.5秒失败，此前完整读取3407872/4194304字节；未生成完成备份或写入。0.1.2准备镜像重新核对SHA256一致，仍未刷入，也未请求本次覆盖确认。随后有效生产BLE重绑成功，0.1.1/hid_ready=false；未执行手机动作。分层诊断实机检查继续受阻，2.1/2.2不勾选。

2026-10-13用户确认已换主机USB口后，仅执行一次新的生产完整备份。串口仍COM5，识别同一ESP32-D0WD-V3 rev3.1、4194304字节，与此前保存身份一致，仅esp32dev兼容。备份384.3秒完成；下载完整4194304字节，SHA256为a2750e22b790136d60d8b640d5933eb103eba67b37049d163ffb9d5bbe88e22e，与响应X-Firmware-SHA256和记录一致，文件保存ignored本机目录。没有Flash写入；这证明本次新USB条件下完整传输成功，不能确定此前根因或保证长期可靠。BLE0.1.2四个catalog镜像实际长度/散列核对通过，应用BIN1143248字节、SHA256为84d0664dcecce24667e08ee6ce499294eea49399ffd2219c93dabd098578b51f；等待新覆盖确认，手机就绪及坐标仍待验证。

本次仅执行新USB条件下实机验收并补证据，没有修改实现或依赖。strict全部18项通过，check_changes覆盖100文件通过，git diff --check退出0。未重复已通过软件回归；0.1.2覆盖及手机输入尚未执行。保守备份变更的完整下载验收任务现已完成，可归档；BLE分层诊断和手机任务变更仍活动。

2026-10-13用户明确授权覆盖0.1.2后，使用上述新完整备份对应未过期一次性ticket执行一次生产write，23.2秒完成，image_verified=true。无重复写入。生产串口第一次绑定成功，firmware=0.1.2、link=true、authenticated=true、keyboard_subscribed=false、mouse_subscribed=false、auth_error=null、hid_ready=false。这确认实际BLE链路与认证正常，两个报告未订阅；没有发送任何手机输入或迁移旧校准。用户回复已重新连接后，主机发现串口断线，一次显式COM5重绑成功，分层状态仍相同；请求手机忘记设备后重新配对，同时保持串口连接观察订阅。无线ADB此时发现一台授权Redmi手机，未用ADB替代HID输入。私密证据保存在ignored new-usb-*.json/bin；旧故障根因和新版坐标精度仍未确认。

## 0.1.2实际恢复与输入（最新）

手机忘记设备重新配对后，显式COM5重绑：link/authenticated/keyboard_subscribed/mouse_subscribed均true、hid_ready=true。实际两次Tab焦点后一次agent-test-123原文输入与截图/DOM一致，板上574ms。

无点击定位100/100在第二、第三次截图像素相同，350/600两次落点相同；450/900、250/450及回到100/100也已观察。当前竖屏校准514/1143计数。生产tap命中左上、中心、右下三个目标（实际鼠标down/up/click各一次）；耗时2786/4540/5409ms。Android相对鼠标仍有加速/落点偏差，不保证像素级小目标或全机型精度。

5000ms长按实际5010.3ms、1000ms长按实际1013ms，释放buttons=0；700ms滑动拖动紫色目标、实际按下819.5ms；scroll -3实际滚动0→112.35555 CSS px。早期事件观察脚本用performance.now最大值匹配了旧页面事件，不算中途停止证据；后改用事件数组索引观察新pointerdown。

修复前长按/拖动实际停止后held137/330.3ms即pointerup/buttons=0，但动作HTTP500。独立OpenSpec report-manual-stop-cancellation已修复并归档；生产复验动作409、stop200/hid_release_sent，手机held133.9/282.9ms释放，无未知动作重放。私密原始文件012-*、stop-fix-*只保留ignored目录。

备份/写入失败历史保留；新USB口本次完整4MB成功不证明原失败根因或长期可靠性。Android16/17、其他品牌、S3实物、旋转/拔线过程仍未验收。

当前完整Python3.12/3.10回归各235通过/1 Windows权限skip/1依赖warning；新增locate外层取消后相关各26通过，源码Ruff通过。最新strict19项与范围124文件通过；已完成本变更限定的实物检查，后续模型、其他系统/板型仍单独待验证。
