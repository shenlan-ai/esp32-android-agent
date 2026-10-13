## 软件与构建

- Python3.12.14与3.10.21：`python -m pytest server/tests -q`，各172 passed、1 skipped、1依赖弃用警告。Windows文件symlink权限相关跳过不代表Linux验证。
- 两个Python环境：`python -m unittest discover -s scripts/tests`，各43 passed，包含实际C++动作调度器27场景；覆盖50ms正向/拖动、600ms无阻塞等待、取消、回绕、最坏两段移动在60秒期限内。
- `python -m ruff check server`及修改工具按`--config server/pyproject.toml`检查：通过。全局扩展风格配置的广泛脚本检查存在既有问题，未扩大范围修改。
- 四板PlatformIO编译成功，日志保留本机`ble-pacing-build.log`及`usb-shared-pacing-build.log`；共享调度器修改后均已重建。
- 新目录`.runtime-local/firmware-pacing-20261013`已收集四板catalog。经典BLE应用镜像SHA256：`a609a0aae462b34a71908ed01eb3dc709def843bbcddacec6d2f2a26e10155a4`；握手版本0.1.1。
- `openspec validate --all --strict --no-interactive`：17项通过；`python scripts/check_changes.py`：修改范围通过。

## 实机与限制

旧BLE0.1.0的三次相同原始定位在直接新截图中落点不同，详见活动实机验收报告。0.1.1的50ms/600ms是保守待验参数，软件测试和编译不证明安卓指针精度已修复。

用户本轮明确确认覆盖。原ticket过期后重新identify与完整backup，通过生产下载接口核对4194304字节、HTTP SHA256及备份记录一致；备份SHA256为`181c14f9bed3ed9b7812ceb9481eefccea43d634a0b50b468da3a1806eb96bdb`。生产write只发送一次，阶段written、image_verified=true，写入及读取校验用时23.2秒。原始备份及job证据位于忽略目录，无ticket或设备标识提交。

写后首次hello超时；停止维护并通过串口RTS重启（不写Flash）后，握手确认0.1.1。生产BLE重新绑定成功、旧校准未开放坐标能力，但hid_ready=false；手机蓝牙设置显示已连接，尚待用户断开重连或重新配对。ADB准备点击被系统INJECT_EVENTS权限拒绝，没有执行手机输入。未验收新版重复定位、校准、长动作释放或真实模型任务，不归档此变更，不交付旧便携包作为新版。

用户随后确认重连，旧会话因板上会话变更拒绝操作；显式重新绑定后串口connected=true、firmware=0.1.1，但hid_ready仍false。需要进一步区分完整重新配对与固件重连问题，已请求确认是否忘记后重新配对；此时未发送定位、点击或文字，未重复刷写。

## 未知版本回归

- 实际假串口与认证TCP握手覆盖缺失、null、对象、unknown/UNKNOWN、空串、非法空白、65字符；均保持连接与键盘、拒绝坐标且不发点击。合法开发标识和64字符版本可绑定校准。
- BLE/USB API保存未知版本返回409/detail，现有controller校准、内存preferences和磁盘文件不变；公开状态无坐标能力，文字仍只发送一次。
- 更新后Python3.12.14与3.10.21完整server回归各200 passed、1 skipped、1依赖弃用警告。新增测试最初误用400/error断言，改为实际409/detail后通过。
- 在server工作目录执行`python -m ruff check android_agent tests`通过。根目录显式config检查因项目first-party发现差异报既有导入排序问题，没有扩大范围修改。
- 最新`openspec validate --all --strict --no-interactive`：16项通过；`python scripts/check_changes.py`：32个修改文件范围通过；`git diff --check`通过（仅Windows换行提示）。

## 0.1.2实际恢复与输入（最新）

手机忘记设备重新配对后，显式COM5重绑：link/authenticated/keyboard_subscribed/mouse_subscribed均true、hid_ready=true。实际两次Tab焦点后一次agent-test-123原文输入与截图/DOM一致，板上574ms。

无点击定位100/100在第二、第三次截图像素相同，350/600两次落点相同；450/900、250/450及回到100/100也已观察。当前竖屏校准514/1143计数。生产tap命中左上、中心、右下三个目标（实际鼠标down/up/click各一次）；耗时2786/4540/5409ms。Android相对鼠标仍有加速/落点偏差，不保证像素级小目标或全机型精度。

5000ms长按实际5010.3ms、1000ms长按实际1013ms，释放buttons=0；700ms滑动拖动紫色目标、实际按下819.5ms；scroll -3实际滚动0→112.35555 CSS px。早期事件观察脚本用performance.now最大值匹配了旧页面事件，不算中途停止证据；后改用事件数组索引观察新pointerdown。

修复前长按/拖动实际停止后held137/330.3ms即pointerup/buttons=0，但动作HTTP500。独立OpenSpec report-manual-stop-cancellation已修复并归档；生产复验动作409、stop200/hid_release_sent，手机held133.9/282.9ms释放，无未知动作重放。私密原始文件012-*、stop-fix-*只保留ignored目录。

备份/写入失败历史保留；新USB口本次完整4MB成功不证明原失败根因或长期可靠性。Android16/17、其他品牌、S3实物、旋转/拔线过程仍未验收。

当前完整Python3.12/3.10回归各235通过/1 Windows权限skip/1依赖warning；新增locate外层取消后相关各26通过，源码Ruff通过。最新strict19项与范围124文件通过；已完成本变更限定的实物检查，后续模型、其他系统/板型仍单独待验证。
