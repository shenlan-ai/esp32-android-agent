# 实机验收与首版完成条件 / Physical acceptance

首版完成需要至少一套真实手机、开发板及模型任务证据。下面的空模板默认**未执行**。板上通信、编译、软件测试、DEMO和便携smoke是不同证据，不能替代手机输入。当前真实状态见 [兼容表](COMPATIBILITY.md)。

Version 0.1 needs at least one real phone/board/model acceptance record. This is an unexecuted checklist, not a passed report. Firmware flashing, board communication, simulation and packaging do not prove phone-side input. Keep Android 15/16/17 targets separate from the specific devices actually tested.

进行中的实际记录见 [Redmi Note14 / Android15 / 经典ESP32](acceptance/2026-10-13-redmi-note14-ble.md)，其中保留输入法转换和坐标校准失败。贡献者可用`scripts/phone_input_fixture.py`准备无外部提交的本机输入页面，具体准备与清理见 [BLE说明](BLE-SETUP.md)。模板仍是待执行清单，不因新增部分证据自动全部通过。

## 1. 条件 / Conditions

复制下列字段到本机报告，保留代码与环境版本。不要填API Key、无线配对码、Wi-Fi密码、完整设备MAC/序列号或私人截图。给设备使用测试编号即可。

| 字段 / Field | 实际记录 / Actual value |
|---|---|
| 日期、测试者 / Date, tester | 未填写 / Not recorded |
| 代码commit；便携release.json版本与dirty / Code revision, release version/dirty | 未填写 |
| 主机系统、Python或便携版本、ADB版本 / Host, runtime, ADB | 未填写 |
| 手机测试编号、厂商/型号、Android/API / Phone label, make/model, Android/API | 未填写 |
| 板子商品型号（未知就写未知）、芯片、Flash、固件版本 / PCB, chip, flash, firmware | 未填写 |
| ADB连接：USB/无线；控制：ADB/BLE/USB / Screenshot transport and control mode | 未填写 |
| S3接口、OTG、供电；或经典板串口桥 / S3 native port/OTG/power or classic UART bridge | 未填写 |
| 屏幕尺寸/方向、指针设置、校准计数 / Frame dimensions/orientation, pointer settings/calibration | 未填写 |
| 模型服务与模型名称、规划是否独立、预算 / Provider/models/planner/budgets (no keys) | 未填写 |
| 可公开的日志/截图编号；隐私处理 / Shareable evidence labels and redaction | 未填写 |

版本可用 `python -m android_agent --diagnose`、`adb version`、`git rev-parse HEAD` 或便携包 `release.json`核对。手机型号、Android版本和API可从系统设置/已授权ADB只读getprop查询；实际值不由适配目标自动填入。CLI命令使用实际ADB路径与设备选择，避免多手机时查询错设备。

## 2. 手动控制和生命周期 / Manual input and lifecycle

逐项写“通过/失败/未执行/结果未知”，附观察与条件；缺少证据的项目不能勾为通过。每种声明可用的控制模式单独执行，不用ADB结果证明BLE/USB。

For each claimed mode, record Passed / Failed / Not run / Unknown, plus the actual observation. Use harmless screens and empty local text fields. Restore the same phone and mode after interruption; never replay an unknown input without observing it.

| 项目 / Check | 可观察证据 / Evidence required | 结果 / Result |
|---|---|---|
| 手机授权与画面 / Authorized screenshot | 正确手机、完整画面和实际方向；离线/未授权不输入 | 未执行 |
| 主控制路径 / Explicit control | 当前模式正确；板子断线后不自动切ADB | 未执行 |
| 板子对应手机 / Board-phone association | 人工确认BLE配对或实际OTG插入；USB枚举本身不算身份确认 | 未执行 |
| 校准 / Calibration | 保存当前尺寸/模式；中心及多个边缘安全目标命中 | 未执行 |
| 点按 / Tap | 人工看到目标响应，记录命中与偏差 | 未执行 |
| 滑动、滚动 / Swipe, scroll | 起止与方向正确，无持续按下 | 未执行 |
| 长按 / Long press | 观察到长按效果及释放；记录实际耗时 | 未执行 |
| ASCII输入和基础键 / ASCII/key | 空字段准确一次输入，未提交；记录实际可用键 | 未执行 |
| 停止 / Emergency stop | 长动作期间停止，分别记录板上清理和手机上键鼠释放 | 未执行 |
| 控制断线、心跳失效 / Control loss | 清空旧动作/释放；恢复后显式重绑，不重放 | 未执行 |
| 画面丢失/受保护 / Screen loss | 自动任务暂停；恢复前无继续点击 | 未执行 |
| 旋转/分辨率改变 / Rotation | 旧坐标与不适用校准被拒绝；重校准后复验 | 未执行 |
| 暂停/接管/恢复 / Takeover | 等明确暂停再手动；恢复重新观察，不复用旧建议 | 未执行 |
| 服务/网页恢复 / Service/page recovery | 网页重开可读取状态；服务退出释放输入，重启不重放任务 | 未执行 |

精度报告只有在测试场景能观察实际落点坐标时才记录像素误差；否则记录目标命中情况和观察方法，不填虚构误差。BLE/USB相对鼠标不承诺所有机型上的精确触摸时序。没有实物断线/释放证据时，保留“未执行”或“未知”。

Record pixel error only with an observable coordinate test surface; otherwise report target hit/miss and the observation method. Relative HID does not guarantee touch timing across phones. Software release acknowledgements cannot prove the phone received a neutral report after disconnection.

## 3. 模型任务 / Model tasks

先通过手动控制，再按 [示例](EXAMPLES.md) 准备起始画面。模型连接测试与真实任务是两项检查。不能只把服务端的completed当成人工确认成功。

| 尝试编号 / Attempt | 模式、起始条件、完整目标 / Mode/start/goal | 模型状态 / Agent state | 人工可见结果 / Observed result | 动作、耗时、恢复、用量 / Actions/time/recovery/usage |
|---|---|---|---|---|
| 未执行 / Not run | 未填写 | 未填写 | 未填写 | 未填写 |

每次实际尝试都记录，失败与未知结果不从分母删除。单独汇总：尝试数、人工确认成功数、失败数、未知数、模型误报completed数。成功率=人工确认成功数/实际尝试数，并注明机型、模式、模型、起始条件与样本量。没有尝试时写“未验收”，不写0%或100%。

Record every actual attempt, including failures and unknown outcomes. Report human-confirmed successes divided by all actual attempts, and separately count false `completed` claims. Include sample size and conditions; no attempts means untested, not a measured success rate.

耗时来自任务记录与独立观察：分别记模型请求、控制动作、完整任务、暂停时间和断线恢复。超时/未知输入不得简单标为“未发生”。Token优先记录供应商usage，估算标明estimated；费用只在实际单价/账单可获得时注明来源和日期，没有信息就写未知，不把预算当成硬账单上限。

Report model, action and task latency separately, along with pauses and recovery. Label estimated token usage. Cost requires an actual dated price/bill source; otherwise mark unknown. A token budget does not prove the bill was capped.

## 4. 固件安装 / Firmware installation

若需要换固件，先按 [安装说明](PORTABLE.md) 完整备份、下载和确认覆盖。不要为了填清单重复刷当前正常板。实际安装记录需包括芯片/容量、所选profile、原Flash完整长度/SHA、明确确认、写后读取校验及失败恢复结果。原Flash可能含秘密，不公开上传。没有S3实物时，不能把已编译S3镜像或模拟写入记为实物通过。

Use full backup and explicit confirmation only when firmware replacement is needed. Do not reflash a working board just to complete this checklist. Record identity/profile, full backup size/SHA, confirmation and read-back result; keep flash contents private. Compiled S3 images and fake-ROM writes are not S3 hardware acceptance.

## 5. 首版审计 / Release audit

| 条件 / Gate | 当前可用于证明的证据 / Required evidence |
|---|---|
| ADB体验和ESP32主路径可用 | 同一真实手机上的画面、手动输入、完整任务与人工观察记录 |
| 停止/断线/恢复可靠 | 上表实际释放、画面丢失、未知输入与重绑结果 |
| 最近三代适配声明准确 | Android15/API35、16/API36、17/API37的具体已测机型；未测仍注明 |
| 开源上手与便携交付 | 中英文入口、四板配置、独立工具许可/来源、解压启动与无系统Python/ADB烟测 |
| 代码与治理 | 对应OpenSpec、适合的测试/Ruff/构建、干净提交、实际运行的CI结果 |
| 性能与成本 | 真实样本、明确条件、人工成功率/延迟/恢复/用量来源 |

满足这些证据前，项目保持开发状态。发布到GitHub或上传报告是独立外部动作；本清单不会自动发布，也不会把本机配置校验冒充远程CI。贡献者见 [开发流程](DEVELOPMENT.md)；现有兼容表只记录已经发生的验证。
