# 可复现上手示例 / Reproducible examples

先按 [中文使用说明](AGENT-USAGE.md) 或 [English usage](USAGE.en.md) 完成画面与手动输入验证。每个示例都通过网页由用户发起；示例文档不会自动操作手机。首次使用较小预算，例如最多10个动作、120秒，并观察任务过程。任务结果还需人工检查。

Start with a small budget (for example 10 actions and 120 seconds), watch the task, and verify the outcome yourself. These are user-initiated goals, not scripts or accepted compatibility results. ADB needs no board; BLE/USB require manual acceptance and saved calibration first.

## 1. 查看 Wi-Fi 状态 / Observe Wi-Fi status

起始条件：手机解锁，处于有“设置”入口的主屏幕，画面可见。任务不修改网络设置。

> 打开设置，进入 Wi-Fi 页面，告诉我 Wi-Fi 开关是否开启。只查看状态，不改变开关或网络，不输入密码。

> Open Settings, navigate to the Wi-Fi page, and report whether Wi-Fi is enabled. Only observe; do not change a switch or network or enter a password.

成功证据：最后截图显示 Wi-Fi 页面及可判断的开关状态，回答与截图一致。不同厂商的“网络和互联网”等层级由视觉模型查找；页面不存在、受保护或判断不清时应暂停/失败，不能猜测状态。BLE/USB不预设Home/Back导航能力，使用可见入口与已声明动作。

Success requires a visible Wi-Fi page, an observable state, and an answer consistent with that screen. OEM menus differ. Ambiguous/protected screens are not success; no private navigation shortcut is assumed for HID.

## 2. 不提交的 ASCII 输入 / ASCII input without submission

起始条件：人工打开一个空白、非密码、不会自动提交的本机文本字段，点入获得焦点。不要使用已有私人笔记、聊天发送框或在线表单。若没有合适字段，跳过此示例并记录未执行。

> 在当前已获得焦点的空白文本框中输入 agent-test-123。只输入，不按回车，不发送、不提交，也不要改动其他内容。

> Type agent-test-123 into the currently focused empty text field. Only type; do not press Enter, send, submit, or change other content.

成功证据：截图中可见且恰好出现一次 `agent-test-123`；没有提交或发送动作。出现不确定输入时先看实际内容，再人工清空/恢复；不要自动重输。当前基础输入仅支持ASCII，不能用此结果宣称中文输入通过。

Success requires exactly one visible `agent-test-123` and no submission. Inspect uncertain input before recovery. This only checks ASCII; Unicode is not a current capability.

## 3. 暂停接管和恢复 / Pause, take over, resume

起始条件：使用第1个观察任务，并停留在安全设置页面。任务较快结束时，不据此判定暂停失败；重新准备能观察到执行过程的任务，再记录实际时序。

1. 任务运行时点击“暂停并接管”，等待明确暂停状态；不要在“正在暂停”时发送手动动作。
2. 在同一手机、同一模式中进行一次无副作用的手动滚动，观察画面。
3. 继续任务，确认重新观察/规划，旧建议没有被盲目重放；最后按完整目标核验。

Pause and wait for the acknowledged paused state; manually scroll once on the same phone/mode; resume and verify fresh observation and the complete goal. An already submitted input can have an unknown outcome. Treat the pause request and phone-side release as separate observations.

## 无设备演示 / Offline demonstration

从仓库根目录安装开发依赖并启动（使用已建立的虚拟环境Python）：

```text
python -m pip install -e "./server[dev]"
python server/tests/agent_demo.py
```

打开 `http://127.0.0.1:8892`，确认页面标有DEMO。模拟手机和模型会演示打开Wi-Fi页；可测试正常速度、慢请求暂停、恢复和导出。说明文字是固定脚本，模型IO是MockTransport；没有真实手机、开发板或付费接口。截图与模拟记录在 `.runtime-local/agent-demo`。停止该进程后才启动同端口其他DEMO。

Open `http://127.0.0.1:8892` and confirm the DEMO banner. The fake phone/model exercise the Wi-Fi task, pause/resume and export. Model explanations are scripted. No physical ADB, board port or external model is used. This demonstrates software behavior, not real input accuracy or success rate.

固件向导另有 `python server/tests/firmware_demo.py --port 8892`，使用临时模拟Flash；USB配网演示为 `python server/tests/usb_demo.py`。模拟下载的Flash备份不能用于恢复实物板。

记录真实验收时使用 [验收模板](ACCEPTANCE.md)。不要把DEMO完成状态记为实机通过。
