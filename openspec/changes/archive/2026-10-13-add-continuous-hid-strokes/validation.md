# 验证记录

实现前读取AGENTS、架构、正式agent/BLE/USB规格及无活动变更状态。上游README/agent/phone明确包含path/circle，当前仅swipe。对0.1.3真实task与phone事件逐笔比对，端点多数偏差0–14px；第4结束请求y1704与第5起点y1747.2本身有43.2px差距，第6起点也偏离前段。连续路径补齐表达能力，不以此诊断声称全部误差来源或任务必成功。未修改上游、未调用新模型或刷写。

## 软件验证（2026-10-13）

- `.venv/Scripts/python.exe -m pytest -q server/tests`：295 passed、1 skipped、1 dependency warning，31.63s。Windows符号链接权限测试跳过。
- `.runtime-local/python310/venv/Scripts/python.exe -m pytest -q server/tests`：295 passed、1 skipped、1 warning，34.27s。
- 最后测试文件仅整理导入后，USB及stroke针对性回归61 passed。
- Ruff（`--config server/pyproject.toml server scripts tools packaging`）通过。
- `unittest discover scripts/tests`：57 passed，无跳过；包含实际g++共享调度器编译运行。
- Node geometry及board-status测试：5 passed。
- PlatformIO四板构建通过：esp32dev程序1137817/RAM39380B；S3 DevKitC和Zero程序738321/RAM56984B；XIAO程序724773/RAM56536B。
- 收集catalog后复核所有镜像SHA256。esp32dev firmware.bin为1144400B，SHA256 `d459fc6b922c9537d98054c1211673022e04a594ee604ef4aee404597b04e7c7`。
- `openspec validate add-continuous-hid-strokes --strict --no-interactive`通过；`python scripts/check_changes.py`通过，178个修改文件在已声明范围内。
- `git diff --check`通过，仅现有Windows换行提示。

模拟和编译不代表实机兼容；新BLE0.1.4/USB0.1.2尚未实机验收。未执行远程CI、新版便携包构建或其他手机/USB板实测。当前COM5仍为0.1.3；新完整4MB备份正在运行，未授权/未执行新版本覆盖。笑脸旧尝试未达到最终目标，保持失败记录和独立最终核验要求。

## 实机准备及工具修复（续）

- 本次完整4MB备份381.5s，下载4194304字节；SHA256与向导及响应头一致：`122300df233dcaedb70b251ddb8deec094da75011096ab82949367f9891728e4`。用户明确授权0.1.4，未过期一次性ticket单次写入；23.2s读取校验通过。新版握手0.1.4，旧校准无效，未迁移旧数据。
- 用户重连后旧会话失效；生产COM5显式重绑成功，link/authenticated/keyboard_subscribed/mouse_subscribed及hid_ready均true。新坐标校准与连续路径实测待执行。
- 原HTTPServer因浏览器闲置连接阻塞/state访问。先补提案/设计/任务/范围并strict校验，再改ThreadingHTTPServer、5秒连接超时与共享快照锁。
- 新真实TCP测试在Python3.12和3.10各2 passed；完整工具测试59 passed，11.738s，全源码Ruff通过。测试覆盖空闲浏览器连接并存、事件写入、并发快照及有界事件列表。
- 自动审批拒绝停止旧8894测试服务的命令，未尝试绕过；在8896启动修复后服务并建立reverse，旧服务仍在。最新截图停蓝牙页，新fixture尚无事件；不记为输入通过。私密原始证据仅ignored strokes-014-*。
- 最后文档更新后，正式规格strict校验16 passed；活动变更strict通过，范围检查179个修改文件通过，`git diff --check`通过。任务2.1校准部分及2.2/2.3仍未完成，未归档。

### 0.1.4当前手机连续轨迹与停止结果

0.1.4无点击边缘定位528/515/531与1173/1176计数截图后，新保存531/1176、1080×2400竖屏且绑定0.1.4的校准。准备时手机曾短暂旋转，未保存横屏校准，不能声称横屏输入通过。通过生产BLE点击浏览器地址栏，输入本机8896地址并Enter，截图与新DOM事件确认LOCAL TEST页面；未用ADB输入。

闭合path为[[120,600],[450,570],[480,620],[200,610],[120,600]]、duration700：板上elapsed8440ms/held2834ms，真实手机1次down/1次up/53次held move，手机held2863ms，末尾buttons=0，首尾差约0.005屏幕px。circle中心300/585、半径65：elapsed7085ms/held1651ms，1次down/1次up/31次held move，手机held1647.2ms，首尾CSS位置相同，末尾buttons=0。这只证明这两笔的按住连续性与闭合，不保证所有圆形精度。

另一次多段path在第一段峰值x173.50CSS px后，实际第二段已回退至138.66时发出stop。动作HTTP409，stop HTTP200/cancelled=true/hid_release_sent；共31次held move，手机held1595.6ms后up/buttons=0，释放之后无后续按住事件。未重放取消笔划。新事件按数组索引隔离，避免旧页面performance.now混淆。

原始备份、校准截图、动作/事件/停止记录保存在ignored strokes-014-*。随后BLE导航至8897空白白板，stroke_count=0与独立截图一致，开始一次有限自然语言VLM笑脸复测，结果待记录。

### 0.1.4真实VLM白板笑脸通过

生产TaskRunner使用用户配置deepseek-flash，从8897空白本机白板开始；自然语言目标未提供坐标或预置图案。114.91秒、11次模型调用、25887真实tokens、3次真实BLE动作（两次circle与一次7点path）。一次非法模型动作在输入前被拒绝，有限恢复后继续；独立goal_check确认两眼和连续上翘的V/U形嘴清晰可见，任务completed、hid_release_sent。手机白板真实stroke_count=3、采样17/16/36点，与独立干净截图一致。路径嘴有折线棱角，并非精细平滑曲线。

这次通过的是手机Edge中的开源本机白板，不冒充原生绘图App；只有一次完整成功，不构成模型成功率或所有手机兼容声明。strokes-014-smiley-task/events/result/export保存在ignored验收目录，历史失败仍保留。

原生hello首轮从浏览器开始：21.03秒、6模型调用、7779tokens、0动作；连续三次非法/不支持动作被拦截，任务failed，未输入文字。手动生产BLE从可见底部手势区上滑到最近任务，截图已出现笔记卡片；随后开始一次原生笔记有限复测，未以本机网页笔记替代。

### 原生hello的有限复测与恢复

第二轮81.78秒/8调用/24600tokens/2动作，模型点击最近任务中的旧绘图草稿并输入hello，违反新建约束；观察后立即生产stop，任务stopped/hid_release_sent，未标为通过。输入前截图显示0字与原有测试绘图；手动清除本次新增文字，五次backspace后实际仍有h（1字），据新截图再发一次backspace，确认0字。退出草稿后稳定列表仍只有旧hello，未删除或修改该已保存笔记。无把未观察的HID完成当成恢复成功。

第三轮从稳定原生列表开始，明确新建及禁止改旧hello；模型实际点击新建、在新空白正文输入一次hello，截图显示5字且标题留空。86.03秒/12调用/24352tokens/4动作：输入步骤verified，但保存/返回的预期未确认，最终非法/不支持动作使任务failed，没有独立goal_check通过。这证明新建内容已达成，不能称完整任务闭环成功；不继续重复创建或付费盲重试。一次只读诊断未执行模型建议，返回合法tap，3346tokens，不能据此判定此前协议错误根因。

有限两个case复测已执行：白板完整VLM成功，原生hello新建内容成功、自动结束失败。软件、固件及当前手机连续笔划/停止验证完成；其他品牌、Android16/17、S3实物、旋转/断线、最新便携包及远程CI仍未验证。历史失败和原始私密证据保留。

归档前最后文档/任务校验：活动strict通过；正式16规格strict全部通过；范围179文件通过；git diff --check通过。无新增实现后重复全回归；2.2以有限真实复测及诚实结果记录完成，不把原生结束失败算为通过。
