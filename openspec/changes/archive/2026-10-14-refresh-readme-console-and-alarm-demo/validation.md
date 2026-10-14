# Validation

日期：2026-10-14（Asia/Shanghai），Windows / Python 3.12.14。

## OpenSpec and documentation

- 阅读 AGENTS.md、正式 MCP 规格与活动变更；执行 openspec list --specs / openspec list。
- 实现和录屏范围变动前更新proposal/design/tasks/files，严格校验当前变更均通过；纯文档/媒体使用skip_specs。
- openspec validate --all --strict --no-interactive：19项通过（18正式规格及当前变更）；--archived --strict --no-interactive：42项通过（本次归档前）。
- git diff --check通过，只有既有LF/CRLF提示。python scripts/check_changes.py：39个文件范围检查通过；保留之前已归档但未提交的变更。
- 控制台PNG来自当前8890实际前端，English、真实手机常规桌面、默认浏览器视口，完整953×965；只遮盖BLE设备标识矩形(358,128,475,153)。未改变DOM、手机内容或任务状态，未使用旧DEMO。
- 中英文README使用前端图，不嵌入手机效果静态图；补齐MCP安装、Codex注册、新会话发现、四工具及全部12类输入、能力子集、观察凭据、核验与停止、两个任务提示词。

## Real Codex + MCP alarm

- 本会话原生android_agent工具读取Redmi Note14 5G / Android15/API35、经典ESP32-D0WD-V3 / 4MB、BLE0.1.4；HID就绪、校准有效。
- 用户返回桌面后继续BLE，从内容页用底部手势/空白点击回到桌面，水平滑动找时钟。系统安装提示通过MCP处理，时钟首次隐私选择由用户处理。
- 每次输入status→fresh screenshot→one android_action→verification screenshot。创建2026-10-15 07:30（手机本地时间），只响一次、开启；原06:00/07:00/08:00保持关闭。
- 保存后核验列表；稍后通过MCP重新打开07:30，更多设置核对只响一次，原值保存并再次观察开启的列表。
- 两次android_stop均返回hid_release_sent，firmware_in_progress=false。
- 保留先前失败：误导航内容页、旧观察/未声明BLE导航拒绝、显式ADB模式home/tap通用device_rejected；底层原因未确定。失败录像不公开，未以ADB注入替代MCP。
- ADB仅只读观察、原生screenrecord、停止本次录屏进程及拉取文件；原始录像和动作日志在忽略目录。

## Media and GitHub playback

- 第一段受Android录屏上限限制，175.47秒只到选择07:30，首次保存发生在录像外。追加66.43秒实录重新打开、核验、原值保存及最终开启列表。
- 拼接共241.90秒，两段间约24分钟未录制；各段原速、不剪切等待。README及来源文档明确披露两段拼接，不称为连续完整创建录像。
- python .runtime-local/mcp-alarm-encode.py通过：H.264 High/yuv420p、720×1512、30fps、无音频、去元数据、fast-start，完整解码通过。
- 闹钟MP4：1,846,045字节；SHA256 4756c688de36f9d5e23fa8cecd5514ac162e03ce9d70c0c0fde4dfa44eeabc7a。
- 抽帧0/55/115/160/174秒和末帧，确认真实时间选择过程及尾部开启07:30列表；无账号、密钥、设备标识或其他应用画面。
- 笑脸MP4复用95.17秒已验收实录，SHA256 9bef42a8e68526bae6994e68e63ffb929ae49323b460cd120f46909c64d787d3。
- GitHub草稿上传授权视频取得真实附件：笑脸34448c64-110a-4feb-ad73-588393730d91，完整闹钟02fe07fa-391f-441d-ad64-e4ba0737bf11；没有提交issue/comment或网页commit。
- 英文README编辑预览真实呈现两个原生video，controls=true、readyState=4、无error，时长95.166667/241.899999秒；闹钟点击后paused=false、currentTime递增。证明截图为忽略目录mcp-alarm-readme-proof.jpg。
- python .runtime-local/mcp-alarm-check-docs.py通过：82个本地Markdown目标/主页锚点、图片尺寸、两个附件嵌入、MCP说明、视频SHA256及moov在mdat前。

## Limits

- 只核验所列实机和保存状态，未等待实际响铃、未验证其他机型/Android16/17/S3。
- 本次纯文档/媒体/临时工具，未执行完整产品回归或固件构建；README引用此前验证不冒充新测试。
- GitHub预览新图片需推送文件后才能显示；本地PNG已视觉核验。Mermaid预览报告Unable to render rich display，不将此用作通过证据。
- 归档后复核全部正式规格/归档/范围；本次未提交或推送。
