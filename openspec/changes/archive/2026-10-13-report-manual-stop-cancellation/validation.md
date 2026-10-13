# 验证记录（进行中）

实机原问题：BLE0.1.2长按停止后页面pointerup/buttons=0，held137ms；拖动held330.3ms后释放，但动作HTTP500。原始记录在ignored .runtime-local/phone-acceptance/012-*-stop-observed.json。没有通过重放未知输入规避错误。

## 修复验证

手动execute/locate只在epoch改变时转换DeviceError，Agent内部和外层取消保持CancelledError。真实ASGI动作/定位并行停止返回409，停止200，动作只发送一次且可开始新的输入；队列旧动作仍拒绝。

Python3.12.14与3.10.21完整服务回归各235 passed、1 Windows symlink权限skip、1既有依赖弃用warning；新增定位外层取消边界测试后执行对应测试。全源码Ruff通过。

生产服务重启并显式COM5重绑，0.1.2四项BLE诊断true；重新保存514/1143竖屏校准。真实长按/拖动在新pointerdown后停止：两个动作HTTP409、stop200/hid_release_sent，实际pointerup/buttons=0，held133.9ms/282.9ms。未重放未知动作，未改固件。私密证据stop-fix-hold.json、stop-fix-drag.json保留ignored目录。仅验证此手机/固件，不宣称普适释放时限。

新增locate外层取消边界后，3.10/3.12相关测试各26通过。strict与115文件范围校验通过，git diff --check退出0（换行提示）。全部任务完成；归档后再校验正式规格。
