# Codex 原生 MCP 笔记笑脸验收（2026-10-13）

OpenSpec：`complete-mcp-action-discovery`。新增发现信息与schema兼容性，输入仍复用内置Agent的Action与唯一DeviceSession。此记录只对下列环境和已发生的操作成立。

## 环境与方法

- Windows主机；Python3.12.14，Python3.10.21回归；MCP SDK1.30.0；Codex CLI0.154.0及实际Codex桌面会话。
- 基线源码5a7e971及本次OpenSpec工作树修改；新会话继承客户端已配置模型，本次没有锁定或单独记录其模型版本，不能据此比较模型成功率或性能。
- Redmi Note14 5G（24094RAD4C），Android15/API35，完整截图1080×2400；经典ESP32-D0WD-V3/4MB/esp32dev/COM5，BLE0.1.4；沿用该手机当前531/1176计数校准。
- 源码工作台8890；本机项目级忽略文件`.codex/config.toml`注册仓库`.venv/Scripts/python.exe -m android_agent.mcp`，没有修改全局Codex配置。
- 在新的桌面会话“通过源码 MCP 在安卓笔记中画笑脸”（`01a13550-f70c-7c02-a0f2-159f36aed08c`）执行用户授权的创建、绘图、保存和重新打开。该会话只调用原生android_agent MCP工具；没有shell、ADB/HTTP替代手机输入，没有修改源码或刷固件。
- ADB仅由工作台内部负责画面采集，实际输入均经ESP32 BLE。不能将“会话未执行ADB命令”误读为项目不使用ADB。

原始会话读取记录、最终MCP图片和工具日志在忽略的`.runtime-local/mcp-notes-*`，不提交私人截图、设备序列号或模型密钥。这里只记录新建笑脸及相关恢复行为；不公开其他笔记内容。

## 动作与视觉结果

状态返回当前9种BLE动作、9个合法键及path/circle规则。新会话根据实际截图导航进入小米笔记，返回列表并新建笔记，进入空白绘图画布；当前黑色画笔。

绘图由4次独立输入组成，每笔前后重新截图：

| 部分 | MCP动作（完整画面0..1000坐标） | 命令耗时 |
|---|---|---|
| 脸轮廓 | circle，中心500/420，横向半径180，duration_ms1500 | 8614ms |
| 左眼 | circle，中心435/395，半径16，duration_ms450 | 5612ms |
| 右眼 | circle，中心568/395，半径16，duration_ms450 | 5668ms |
| 笑嘴 | 一次path：407/435 → 412/448 → 430/460 → 460/470 → 500/474 → 540/470 → 570/460 → 588/448 → 594/435，duration_ms1000 | 6131ms |

上述耗时包含定位、传输及动作，不等于duration_ms或通用性能指标。笔画视觉结果是圆形轮廓、两个小圆眼睛和一条连续向下弯曲的U形笑嘴。没有输入标题，应用将列表条目显示为“图片笔记”。

通过绘图页完成按钮保存，等待“正在保存中”结束，返回笔记列表看到新笑脸缩略图，再重新打开刚创建的条目。最后MCP截图显示该新笔记的笑脸图片仍存在；不是仅停留在未保存画布。主会话随后通过新的源码stdio SDK客户端独立观察，仍看到同一笑脸图片。

最后android_stop返回`hid_release_sent`且`firmware_in_progress=false`。本次桌面会话62次原生MCP调用：15次status、31次screenshot、15次action、1次stop；action包含1次swipe、10次tap、3次circle、1次path，其中1次tap被拒绝。会话总耗时1122.118秒，包含模型思考、页面观察、导航和恢复，不能据此声称快速或一次定位全部正确。

## 失败与恢复证据

- 页面切换后首张截图有延迟，追加观察稳定页面再继续，没有凭命令完成假定页面已切换。
- 第一次保存点击凭据过期，工具状态failed；没有送出旧画面点击。重新截图并根据新观察选择完成按钮，随后保存成功。
- 重新打开时模型选择了错误列表位置，误入一条现有笔记。它发现后没有编辑或输入，立即返回列表，改为顶部的新笑脸缩略图，再完成正确条目的核验。不能宣称全程没有打开其他笔记或模型定位零错误。
- 最终画面与保存核验成功不代表任意任务、应用、手机或模型均自主可靠。保留上述误定位，不将命令执行正确等同语义目标总是正确。

## 发现与软件验证

全部12种内置输入经android_action暴露；MCP四个工具保持统一入口。状态新增当前能力对应的`allowed_keys`、`action_examples`、`action_rules`；done/fail/replan为编排决定，不是手机输入。ADB无连续path/circle，HID无Android主页/返回/最近任务导航动作，遵守实际模式。

初始桌面会话初始化时，Codex工具转换把Pydantic tuple的prefixItems显示成字符串数组；该会话仍成功提交合法整数path，后端严格验证。最终源码改用等价的标准items整数数组、每点恰好2项；新的SDK客户端已检查最终公开schema，运行时仍拒绝字符串、浮点、布尔及越界坐标。

`.venv/Scripts/python .runtime-local/mcp-notes-verify.py`启动另一个全新Codex CLI0.154.0只读会话，通过最终源码MCP仅调用一次status和一次screenshot，退出码0。它从真实图像确认笔记详情中的笑脸轮廓、两只眼睛和笑嘴，确认android_action声明全部12种输入及points为嵌套数值数组。它准确限定单张图不能证明退出/重启持久化；保存链路证据来自前述桌面会话退出并重新打开。该CLI发生两次上游模型流断开（Upstream access forbidden）并重连，最终完成；没有android_action调用，也没有重放手机输入。保留原始日志，不把重连说成一次无误运行。

- MCP专项70 passed，覆盖真实SDK/HTTP、全部动作声明、ADB逐动作输入、BLE/USB笔画转换和整数schema验证。
- Python3.12与3.10各369 passed、1 Windows symlink权限skip、1依赖warning；全源码Ruff通过。
- 没有刷写/重编固件、没有重建便携包或新增其他机型/系统/板型实机证据。

实测后已移除项目配置里本次android_action临时预批准，保留源码注册并恢复默认工具策略；全局配置及密钥保持原样。
