# 验证记录

## 已执行

- 实现前`openspec validate accept-connected-android15-ble --strict --no-interactive`通过，2026-10-13再次校验通过。
- `scripts/phone_input_fixture.py`真实localhost HTTP测试：HTML GET200，畸形JSON POST400，32769B请求POST413；工具Ruff通过。该工具不打开ADB、串口或模型，不作为正常运行入口。
- 真实Redmi Note14 / Android15与经典ESP32 / COM5配对，生产API就绪；真实Tab焦点、文本转换、点击和鼠标REL输入已取得页面事件/截图证据。
- 临时鼠标计数1080/2400未通过落点验收；中文搜狗下ASCII原文失败，均如实记录。用户要求先不实现自动切换输入法，已撤销仅含元数据的空变更，没有代码/固件修改。
- 用户手动切英文并清空字段，取得独立截图；ASCII复验前无线ADB设备消失，取图阶段拒绝，未发出此次文字；仍待恢复。
- 已配置模型的生产`/api/models/test`合成图探测通过：1.047s / 263 tokens / 实际usage；未发送手机图。真实模型任务尚未开始。
- 采集断线后生产空闲stop返回`hid_release_sent`，不作为长动作手机释放证明。
- `python scripts/check_changes.py`通过，11个修改文件；当前范围仅本机fixture、脱敏文档和所属OpenSpec。

## 当时未完成（后续结果见最新段）

手机恢复后ASCII原文样例已通过（DOM、input事件和独立截图一致），但旧固件坐标失败。本轮用户确认后0.1.1完整备份、刷写读取校验及串口握手通过；新固件hid_ready=false，已请求手机人工重连。仍需复验鼠标精度、多目标及长按/拖动/滚动/停止，继续真实模型任务。原始证据在忽略目录，不提交私人标识/密钥。仅有这一手机和经典板的部分证据，Android16/17、S3及其他输入法仍待实机验证。尚未清理测试reverse/forward和fixture，因此变更保持活动状态，不归档、不声称首版完成。

2026-10-13用户确认已换主机USB口后，仅执行一次新的生产完整备份。串口仍COM5，识别同一ESP32-D0WD-V3 rev3.1、4194304字节，与此前保存身份一致，仅esp32dev兼容。备份384.3秒完成；下载完整4194304字节，SHA256为a2750e22b790136d60d8b640d5933eb103eba67b37049d163ffb9d5bbe88e22e，与响应X-Firmware-SHA256和记录一致，文件保存ignored本机目录。没有Flash写入；这证明本次新USB条件下完整传输成功，不能确定此前根因或保证长期可靠。BLE0.1.2四个catalog镜像实际长度/散列核对通过，应用BIN1143248字节、SHA256为84d0664dcecce24667e08ee6ce499294eea49399ffd2219c93dabd098578b51f；等待新覆盖确认，手机就绪及坐标仍待验证。

本次仅执行新USB条件下实机验收并补证据，没有修改实现或依赖。strict全部18项通过，check_changes覆盖100文件通过，git diff --check退出0。未重复已通过软件回归；0.1.2覆盖及手机输入尚未执行。保守备份变更的完整下载验收任务现已完成，可归档；BLE分层诊断和手机任务变更仍活动。

2026-10-13用户明确授权覆盖0.1.2后，使用上述新完整备份对应未过期一次性ticket执行一次生产write，23.2秒完成，image_verified=true。无重复写入。生产串口第一次绑定成功，firmware=0.1.2、link=true、authenticated=true、keyboard_subscribed=false、mouse_subscribed=false、auth_error=null、hid_ready=false。这确认实际BLE链路与认证正常，两个报告未订阅；没有发送任何手机输入或迁移旧校准。用户回复已重新连接后，主机发现串口断线，一次显式COM5重绑成功，分层状态仍相同；请求手机忘记设备后重新配对，同时保持串口连接观察订阅。无线ADB此时发现一台授权Redmi手机，未用ADB替代HID输入。私密证据保存在ignored new-usb-*.json/bin；旧故障根因和新版坐标精度仍未确认。

## 0.1.2实际恢复与输入（最新）

手机忘记设备重新配对后，显式COM5重绑：link/authenticated/keyboard_subscribed/mouse_subscribed均true、hid_ready=true。实际两次Tab焦点后一次agent-test-123原文输入与截图/DOM一致，板上574ms。

无点击定位100/100在第二、第三次截图像素相同，350/600两次落点相同；450/900、250/450及回到100/100也已观察。当前竖屏校准514/1143计数。生产tap命中左上、中心、右下三个目标（实际鼠标down/up/click各一次）；耗时2786/4540/5409ms。Android相对鼠标仍有加速/落点偏差，不保证像素级小目标或全机型精度。

5000ms长按实际5010.3ms、1000ms长按实际1013ms，释放buttons=0；700ms滑动拖动紫色目标、实际按下819.5ms；scroll -3实际滚动0→112.35555 CSS px。早期事件观察脚本用performance.now最大值匹配了旧页面事件，不算中途停止证据；后改用事件数组索引观察新pointerdown。

修复前长按/拖动实际停止后held137/330.3ms即pointerup/buttons=0，但动作HTTP500。独立OpenSpec report-manual-stop-cancellation已修复并归档；生产复验动作409、stop200/hid_release_sent，手机held133.9/282.9ms释放，无未知动作重放。私密原始文件012-*、stop-fix-*只保留ignored目录。

备份/写入失败历史保留；新USB口本次完整4MB成功不证明原失败根因或长期可靠性。Android16/17、其他品牌、S3实物、旋转/拔线过程仍未验收。

最新结论：0.1.2在同一手机上真实ASCII、多目标、长按/拖动/滚动和中途停止已验收；旧失败保留为历史。新的VLM案例属于accept-vlm-notes-and-smiley，原生hello已输入但协议结束失败。Android16/17、其他品牌、S3实物、旋转/拔线仍明确未执行，单机检查完成不等于全兼容。

最终收尾：VLM案例有限尝试已结束，原生hello内容达成但任务failed；笑脸恢复未达标后主动stop，release=hid_release_sent。8894输入fixture与8895案例fixture已关闭，本次reverse8894/8895及DevTools forward9224已移除；仅8890工作台继续监听。生产BLE hid_ready=true、calibrated=true，无自动任务运行，用户配对与设置保留。没有重复刷写或声称鼠标像素精度通过。

最终归档前：`openspec validate --all --strict --no-interactive`19项通过；`openspec validate --archived --strict --no-interactive`26项通过；`.venv/Scripts/python.exe scripts/check_changes.py`138个修改文件范围通过；`git diff --check`退出0（仅Git CRLF提示）。同一代码的Python3.10/3.12回归各239通过/1权限skip/1依赖warning，Ruff、工具57测试和网页5测试通过；之后仅补验收记录，无变化不重复回归。未执行项目及坐标限制均在报告明确保留。
