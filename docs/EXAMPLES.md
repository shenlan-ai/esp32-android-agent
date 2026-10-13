# 可复现上手示例 / Reproducible examples

模型返回输出额度耗尽、过滤、工具调用或拒答时，系统会拒绝本次动作并计入用量，即使正文恰好是完整JSON。恢复受原失败/时间/Token预算限制，不自动扩大额度。输出额度耗尽时检查工作台已保存的模型设置及供应商支持；JSON模式、提高单次额度或模型连通性通过均不代表手机案例通过。未返回结束字段的兼容供应商仍须通过严格动作校验与独立画面核验。

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

## 4. 新建备忘录写 hello

起始条件：用户自行完成原生笔记App首次设置，打开笔记首页；输入法由用户切英文，BLE已就绪并保存当前方向校准。只新建测试笔记，不使用已有私人笔记。

> 创建一条新的空白笔记，在正文恰好输入一次 hello。确认正文后结束，不改已有笔记、不分享、不登录、不改变同步设置。遇到权限/协议弹窗需要人工处理；输入结果不确定时先观察。

成功要求截图中正文恰好为hello。新建按钮或字段未命中、输入法转写、模型格式失败都不能算成功。原生App可能自动保存或按用户原有设置同步；测试工具不能承诺替App关闭这些行为。

## 5. 白板画笑脸

优先使用已有App空白画板。没有画板或原生绘图不支持鼠标时，贡献者可显式启动离线测试工具：

```text
python scripts/phone_examples_fixture.py --port 8895
adb -s <已授权手机> reverse tcp:8895 tcp:8895
```

手机浏览器打开`http://127.0.0.1:8895/`，页面清楚标为LOCAL PHONE EXAMPLES，模型点击Whiteboard进入空白canvas。工具不访问模型、ADB或开发板；图案只由真实pointer事件产生，不预置笑脸。也提供空白Notes备用字段，备用字段验收不能冒充原生笔记App通过。完成后关闭工具、移除本次reverse。

> 打开Whiteboard，在空白画板中画一个清楚的笑脸，有两只眼睛和向上微笑的嘴巴。使用当前已声明的绘图动作，不清除已有画线。观察整个图案后判断是否成功。

当前 BLE 0.1.4 / USB 0.1.2 在校准和能力满足条件时提供连续 path/circle；path 限 2–20 点，整笔最多 500 份运动报告，跨段保持一次按下/释放。ADB 和旧固件不声明这些动作，可用已有 swipe 能力做独立分段测试，不能把分段输入当成连续曲线。模型与人工截图核验均须能认出完整笑脸，任意线条不等于完成，也不保证精细圆弧或复杂绘图。

2026-10-13 最新实测：Redmi Note14 5G / Android 15 / BLE 0.1.4 的本机白板由模型自行选两次 circle 和一次 7 点 path，114.91 秒、3 次真实输入后独立最终核验通过；嘴是有棱角的 V/U 折线。这是浏览器测试白板，原生绘图 App 完整笑脸仍未通过。原生小米笔记新建并输入 hello 达成，但创建任务自动结束失败；曾误选旧测试草稿，经人工清除新增文本和退出后，单独只读保存核验任务通过（133.03 秒、3 次点击）。不称单次全自动稳定通过。旧固件与早期失败记录保留在[完整实机报告](acceptance/2026-10-13-redmi-note14-ble.md)，示例不是保证成功的脚本。

Latest physical evidence: BLE 0.1.4 drew a recognizable smiley on the local browser whiteboard and passed an independent final check. The native hello note was created and later verified in a separate read-only task after manual intervention; its creation task failed to finish automatically. Earlier failures remain documented. These results cover one Android 15 phone only.

若模型使用推理token且完整上下文返回空动作或finish_reason=length，可在模型设置的extra_body中使用现有受限选项`max_completion_tokens`（64～4096）；服务会省略默认max_tokens，保留任务总token/时限预算。当前供应商已通过4096及`response_format: {"type":"json_object"}`、`temperature: 0`的只读探测。供应商不支持这些选项时应恢复原配置，不可把HTTP200或一次合法输出当作全任务通过；详细失败及恢复见报告。
