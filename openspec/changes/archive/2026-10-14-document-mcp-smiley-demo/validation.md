# Validation

日期：2026-10-14（Asia/Shanghai）；Windows、Python3.12.14，Redmi Note14 5G / Android15/API35、经典ESP32 COM5 / BLE0.1.4。

## 流程与范围

- 修改前读取AGENTS、project-governance及mcp-device-tools正式规格、上次验收和README；`openspec list --specs`列出18规格，`openspec list`无活动变更。
- `openspec validate document-mcp-smiley-demo --strict --no-interactive`在媒体/文档及本机恢复校准前均通过；skip_specs明确纯文档与媒体，不改变产品行为。
- 文件范围覆盖两份README、图片/视频/来源说明、本次验收及忽略目录中的本机录制处理文件。已有未提交MCP修改继续由其新归档范围覆盖，不修改旧历史。

## 实机

- 实际原生MCP status确认BLE链路、认证、双通知订阅true、idle、非维护，校准绑定当前调试连接后提供9种BLE能力，path/circle可用。
- 原生MCP工具10次输入全部ok：6tap、3circle、1path，逐动作前后观察。新建独立笔记、空白画布绘图、保存、结束录像、返回列表并重新打开正确新条目成功。
- 页面切换后必要时追加截图，不重放。最终完整轮廓、双圆眼睛、连续U形嘴清楚可见。两次stop返回hid_release_sent、firmware_in_progress=false；最终指针在绘图外，未编辑旧笔记。
- ADB只读机型/系统、原生screenrecord、结束自己录屏进程、拉取与最终screencap；手机输入未用ADB或手动HTTP替代。
- 准备配置首次错误CSRF头403、机型名称断言返回代码而不匹配，已据实际源码/型号修正；媒体首次误认为MCP JPEG是1080×2400，检查得576×1280后改用只读全分辨率PNG，未拉伸低分辨率图片。失败均在准备/处理阶段，不改产品、不跳过保护。

## 媒体与文档

- 本机临时编码工具：`.venv/Scripts/python -m pip install --target .runtime-local/mcp-demo-encoder imageio-ffmpeg==0.6.0`；只有忽略目录，未修改项目依赖或全局环境。
- `.venv/Scripts/python .runtime-local/mcp-demo-record.py start/stop/pull/capture`：录制、正常finalize、下载MP4和只读截图成功。
- `.venv/Scripts/python .runtime-local/mcp-demo-media.py`：裁切实际PNG并转码原生MP4成功。ffmpeg7.1完整解码零错误；图952×424/44,429字节，视频95.17s/720×1512/H.264 High/yuv420p/30fps/473,763字节/无声/faststart。
- view_image检查最终图和0/15/35/55/75/94秒联系表：从空白到轮廓、眼睛、笑嘴、保存结果均为实际手机内容，录像无列表/其他笔记，图片无指针遮挡。连续原速、未剪掉等待，没有添加或修补笔画。
- 两份README、图片说明、视频说明、本次验收共103个本地Markdown文件/锚点均存在，代码块成对；中英文均有可点击图片与MP4、录制日期、边界及任务提示。
- SHA256核验与文档一致：图片`0f629d01b13add49e02e01aa5904eec6fb4117c6c6fbef36107112f59fd312a0`；视频`9bef42a8e68526bae6994e68e63ffb929ae49323b460cd120f46909c64d787d3`；MP4 moov先于mdat，大小低于5MB。
- README最新测试数369/70与complete-mcp-action-discovery归档验证记录一致，明确复用，不伪称本次完整回归。

## 预归档检查

- `openspec validate --all --strict --no-interactive`：18正式规格及1活动变更，共19 passed、0 failed。
- `openspec validate --archived --no-interactive`：41 passed、0 failed。
- `.venv/Scripts/python scripts/check_changes.py`：29个修改文件范围通过；加入本验证记录后再执行最终检查。
- `git diff --check`：通过；只有既有Git LF/CRLF转换提示，无差异空白错误。

完成上述任务后执行`openspec archive document-mcp-smiley-demo --yes`，然后再次检查正式/归档规格和文件范围。归档后的实际结果以本次工具输出为准，不在执行前声称通过。

## 限制与未执行

新录屏是当前会话实机重演，不是昨天独立Codex会话的原录像。录屏不含连接设置、创建或退出重开过程，截图和MCP日志记录重开成功。不以95秒声称整个任务时间或任意手机自主成功率。

本次未改业务源码/前端/固件、未编译或刷写、未重建便携包、未执行完整Python/网页回归或远程CI。复用此前已完成MCP软件验证；新的检查仅为媒体、文档及同机实测。未修改模型设置、密钥或客户端审批策略，未上传私人原始内容。
