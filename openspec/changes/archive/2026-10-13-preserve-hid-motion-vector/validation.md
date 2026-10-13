# 验证记录

## 0.1.3 授权刷写与连接

2026-10-13收到用户明确“现在刷入并继续实测”授权后，沿用同一生产向导已启动的新备份，不重复读取。完整4194304字节备份384.7秒完成；下载长度与SHA256 `38dca27efa2013d17f73b022975deef6b4e2002a5503963750f5210798325340`均与响应头/记录一致，保存ignored `.runtime-local/phone-acceptance/vector-013-authorized-backup.bin`。使用该备份对应未过期一次性票据单次写入，23.4秒后phase=written、image_verified=true。生产COM5握手firmware=0.1.3，没有重复刷写或迁移旧校准。

初次绑定链路/认证true、两种订阅false；用户明确完成重新连接后，旧串口会话失效，显式COM5重绑成功。生产状态link/authenticated/keyboard_subscribed/mouse_subscribed均true、hid_ready=true。实际校准/输入仍待继续，不以该状态冒充手机坐标通过。私密job和状态记录保存在ignored vector-013-*.private.json。

## 0.1.3 手机轨迹与取消实测

同一Redmi Note14 5G / Android15 API35 / 1080×2400竖屏，BLE/COM5控制，无线ADB仅取图。用户手动打开手机Edge本机白板8895。先用无点击locate逐项检查水平480/500/515/528/531与垂直1100/1150/1173/1176计数边缘，保存新版本绑定的531/1176计数校准；没有直接迁移旧514/1143校准。中心tap实际mouse down/up与独立截图一致，约落在(547.5,1209.2)，相对请求(540,1200)存在约8/9像素偏差，不能声称像素级精度。

四次生产swipe依次请求归一化(200,400)→(650,450)、(700,500)→(600,700)、(650,730)→(300,650)、(200,700)→(250,520)。以当前事件数组索引隔离新事件，实际mouse采样31/32/26/29点，每组down后连续运动且up/buttons=0。对实际首尾连线的最大垂距为0.261625/0.292239/0.271685/0.044377 CSS px，DPR2.8125对应约0.736/0.822/0.764/0.125屏幕px；独立截图均为直线，未出现旧轴向尾段。板上elapsed 5664/6387/7825/7721ms，held1566/1550/1285/1402ms；700ms仍是最低按压时长。这里只证明这四组手机轨迹，未覆盖全斜率/品牌/旋转。

另在真实新mouse pointerdown回传后停止5000ms长按和5000ms拖动。两次动作HTTP409、stop HTTP200/cancelled=true/hid_release_sent，手机pointerup/buttons=0，实际held134.6/234.7ms。停止后不重放动作。原始轨迹、校准、截图及停止记录在ignored vector-013-*文件。用于准备页面的ADB打开命令被自动审批拒绝，改由用户手动打开；未用ADB输入替代上述HID验收。

通过生产BLE点击浏览器刷新后，白板实际stroke_count=0、截图空白，启动一次已配置VLM笑脸复验；结果待完成后记录，不把手动轨迹当成VLM成功。

该次deepseek-flash任务最终主动停止：279.92秒、19次模型调用、68433tokens、7次真实swipe；实际白板7笔采样5/5/8/18/11/13/15点。独立截图有两眼，但嘴部间断和交叉，连续修补未改善；任务最终stopped，stop HTTP200/hid_release_sent，保留完整task/export/事件/截图于ignored vector-013-vlm-*。步骤核验曾拒绝不符合预期的嘴部，不能将局部verified或直线修复标为完整笑脸成功。本变更要求的有限复验与真实结果记录已完成，不引入新付费循环或放宽核验；hello按设计未重输。Android16/17、其他品牌、S3实物、旋转及拔线未实测。

## 完成与规范验证

实机结束时生产任务stopped、BLE0.1.3 hid_ready=true、calibrated=true、firmware busy=false，没有后台自动输入。核对进程命令后关闭本次拥有的8894/8895 fixture并移除本次手机reverse映射，保留8890工作台、配对、校准及模型设置。此前四板编译、真实C++轨迹/取消回归与主机版本门禁检查均通过；本轮仅刷写、实机操作及文档记录，未再次执行无代码变化的全套软件测试或重新编译，也未执行远程CI。

归档前`openspec validate preserve-hid-motion-vector --strict --no-interactive`通过；`openspec validate --specs --strict --no-interactive`16通过；`python scripts/check_changes.py`163修改文件范围检查通过；`git diff --check`退出0，仅Git行尾转换提示。所有实现任务完成，VLM失败作为有限实测的真实结果保留；本变更完成不代表项目完整笑脸目标已达成。

## 软件验证结果

- `.venv/Scripts/python.exe -m unittest discover -s scripts/tests`：57通过，无skip；真实g++执行88组轨迹及段切换与已有27场景，BLE诊断7场景。
- `.venv/Scripts/python.exe -m pytest -q server/tests/test_ble.py server/tests/test_usb.py`：85通过，1依赖弃用warning，覆盖固件版本/校准门禁及停止/超时。
- `.venv/Scripts/python.exe -m ruff check --config server/pyproject.toml server scripts tools packaging`：通过。
- `openspec validate preserve-hid-motion-vector --strict --no-interactive`：通过。
- `.venv/Scripts/python.exe -m platformio run -d hardware/ble_bridge`：esp32dev通过，程序1136977B/RAM39212B。
- `.venv/Scripts/python.exe -m platformio run -d hardware/usb_bridge`：三配置均通过，DevKitC/S3 Zero程序737693B/RAM56816B，XIAO程序724149B/RAM56368B。S3无实物验收。
- `.venv/Scripts/python.exe scripts/collect_firmware.py --output .runtime-local/firmware-vector-20261013`：四配置所有镜像SHA256与catalog逐个核验一致。esp32dev应用镜像SHA256为`1a8ddf0b1e8e78e709ce288eb645b4b1652d11e88b01f658980081c4ef399395`；BLE握手源码0.1.3、USB CDC/握手0.1.1。

服务已先停止任务、收到hid_release_sent、切换ADB维护模式后重启加载新catalog，保留原本机数据及模型设置。当前仅启动COM5只读识别，未写Flash。完整新备份及实机待完成，变更保持活动。全服务端/网页回归此前已通过，本次仅固件及文档改变，未重复无关全套。

## 红绿回归

添加逐报告轨迹断言后，旧独立轴截断实现由真实g++编译成功但运行失败（退出3221226505）；失败为`2 * hidAbs(reachedY * steps - y * i) <= steps`断言，证明总位移检查不能替代途中轨迹。实现共同整数进度后，`.venv/Scripts/python.exe -m unittest discover -s scripts/tests -p test_firmware_engine.py`执行2项测试通过、无skip。随后扩充零向量至88组正负轴/定位/拖动轨迹，并要求工具入口核验对应成功输出；扩充后的57项全工具测试通过，无skip。

协议限制每轴±4000，共同步数最多500，整数乘积最多2000000；零向量不进入除法。插值状态在定位到拖动的段切换重置；已有取消、最低时长、BLE/USB节奏和回绕场景保留。以上为报告计数的软件保证，未证明手机像素精度或VLM目标完成。

## 实现前依据

创建本变更前已读取正式BLE/USB规格和旧节奏修复设计；当时无其他活动变更。实机失败截图呈斜向后单轴尾段，共享代码独立hidDelta(dx)/hidDelta(dy)能确定性生成这种错误轨迹；不能因此归因全部模型定位误差。先用真实C++回归证明再修改实现。板上仍BLE0.1.2，未经新授权不覆盖。

## 规范检查

`python scripts/check_changes.py`通过，148个修改文件均有活动或新归档范围；`git diff --check`通过，仅Git行尾转换提示；`openspec validate --specs --strict --no-interactive`：16个正式规格通过。本变更3项软件任务完成，备份/刷写/手机验证仍未完成，不归档。

## 当前板升级准备

2026-10-13生产向导识别COM5为ESP32-D0WD-V3 revision v3.1、4194304B，身份与历史板一致，唯一兼容profile为esp32dev。一次新完整只读备份383.5秒完成；下载4194304字节，SHA256 `38dca27efa2013d17f73b022975deef6b4e2002a5503963750f5210798325340`与响应头及保存记录一致。备份/私密job元数据保存在ignored `.runtime-local/phone-acceptance/vector-013-backup.*`。新catalog已快照至对应job并通过散列校验；板上仍BLE0.1.2，未写Flash。

已准备BLE0.1.3覆盖及后续校准/轨迹验收，须按正式`firmware-installation`完整备份与明确一次性覆盖确认规则取得用户对此版本的授权；先前0.1.2授权不扩展到本次覆盖。票据5分钟过期时需重新识别/完整备份，不能直接恢复旧票据。2.1尚未勾选，2.2/2.3待实机。

## 等待授权期间的运行状态核对

2026-10-13再次读取规范、正式规格及本活动变更，strict通过。生产API确认任务idle、ADB维护模式、无板控制连接且firmware busy=false；`POST /api/stop`返回no_held_input及无刷写。安全重启8890服务，保留原data-dir与新catalog，加载已归档的模型结束信号检查修复；启动后工作台及status/task HTTP均200，任务仍idle、无板控制连接、无刷写。未调用付费模型、未向手机输入、未写Flash。用户对0.1.3的覆盖确认尚未收到，旧票据已过期；没有再次启动耗时备份，仍保留3/6任务和活动变更。本轮正式16规格strict、本变更strict、157修改文件范围检查及git diff --check均通过；仅Git行尾转换提示。
