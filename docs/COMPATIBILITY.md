# 兼容性与验证状态

本页描述当前结论；按版本排列的原始成功、失败与恢复过程见[实机报告](acceptance/2026-10-13-redmi-note14-ble.md)和 OpenSpec 归档。模拟、编译、便携程序启动与真实手机输入是不同层级的证据。

## 当前实机组合

| 项目 | 已验证条件 |
|---|---|
| 主机 | Windows x64，Python 3.12.14，本机 FastAPI 工作台 |
| 手机 | Redmi Note14 5G，型号 24094RAD4C，Android 15 / API 35，1080×2400 竖屏 |
| 开发板 | ESP32-D0WD-V3 rev 3.1，4MB Flash，CP2102 串口桥；商品 PCB 名未知 |
| 固件 / 画面 | `esp32dev` BLE 0.1.4，ADB 截图；校准 531 / 1176 计数 |
| 模型 | 用户配置的 OpenAI 兼容视觉接口，模型名称 `deepseek-flash` |

当前板已完成完整 4MB 备份、下载 SHA256 核验、用户明确确认后的单次刷写与读取校验。重连并显式主机重绑后，链路、认证和键鼠通知订阅均就绪。

| 验收项 | 实际结论 |
|---|---|
| ASCII、点击、长按、拖动、滚动 | 有真实事件与截图证据；基础键鼠来自 0.1.2，后续版本补测如下 |
| 向量保持 | 0.1.3 四组不同斜率拖动未出现旧单轴尾段；中心点击仍约 8/9px 偏差 |
| 连续 path / circle | 0.1.4 闭合多段 path 与 circle 一次按下/释放、连续运动、末尾 buttons=0 |
| 动作中停止 | 长按/拖动及 0.1.4 第二段运动中停止释放；动作 HTTP 409，stop HTTP 200，未重放 |
| VLM 白板笑脸 | 0.1.4 手机 Edge 本机白板：2 circle + 1 path，114.91 秒、3 次输入，独立最终核验通过；嘴为折线 |
| 原生 hello | 新笔记输入达成，创建任务自动结束失败；误选旧测试草稿后曾人工清理。人工退出后，单独只读任务核对保存通过（133.03 秒、3 点击） |
| 原生绘图 App 完整笑脸 | 未通过；浏览器白板成功不能替代这一结论 |

这里只覆盖这台手机的上述条件，不构成全屏像素精度、长时间可靠性或模型成功率保证。原生 hello 尚未证明单次全自动稳定完成。

## Android 与开发板

目标覆盖 Android 15 / API 35、16 / API 36、17 / API 37；目前仅上述 Android 15 手机有实机证据。其他品牌/机型、Android 16/17、旋转校准与拔线过程仍待验收。基础输入为可打印 ASCII，用户自行切英文输入法；自动输入法切换和 Unicode 输入未实现。

| 配置 | 路线 | 证据与限制 |
|---|---|---|
| `esp32dev`，经典 ESP32 / 4MB | 串口 + BLE HID | 当前 D0WD-V3 芯片实测；其他商品板需核对容量、供电与布局 |
| `esp32_s3_devkitc`，S3 DevKitC-1 N8 / 8MB | Wi-Fi + 原生 USB HID | USB 0.1.2 编译与主机协议模拟通过，手机实测待完成 |
| `xiao_esp32s3`，XIAO S3 / 8MB | 同上 | 同上 |
| `esp32_s3_zero`，S3 Zero / 4MB | 同上 | 同上；通用配置无 PSRAM/GPIO 依赖 |
| ESP32-S2 | 原生 USB 芯片能力 | 未提供当前已验收配置 |
| ESP32-C3 / C6 / H2 | 可考虑 BLE | 未提供当前已验收固件；USB Serial/JTAG 不等于 USB HID |

CP2102 / CH340 是串口桥，无法据此选择 S3 固件。芯片信息不能识别商品 PCB 名。经典板通过 BLE 控制手机，可同时用 USB 或无线 ADB 截图；S3 占用手机 USB 时须使用无线 ADB。详见[板型识别](BOARD-IDENTIFICATION.md)、[BLE](BLE-SETUP.md)、[USB](USB-SETUP.md)。

S3 的挑战认证、会话、心跳、取消、未知结果不重放、显式重连以及 CDC 配网身份检查已模拟验证；中英文配网和校准页面通过离线浏览器验收。没有 S3 实物参与，USB 枚举也不能证明具体手机身份。

## 软件与分发验证

最新能力示例筛选基线的 Windows Python 3.10.21 / 3.12.14 回归各 **299 passed、1 symlink 权限 skip**，另有一条依赖弃用警告；全源码 Ruff、59 工具测试、5 网页测试与四板构建通过。测试使用假设备和模型，不调用付费服务；完整共享固件 C++ 检查在依赖齐全时真实编译执行。发布准备会在对应 OpenSpec validation.md 记录最终检查。

历史 Linux 基线已在本机 Debian 13 容器 Python 3.12.15 与 Debian 13.7 / Python 3.10.22 实测：各 231 服务端、57 工具测试，无 skip，包含 g++ 真实固件检查；Node 容器的 5 网页测试通过。仅核心依赖的真实 CLI/HTTP 启动也通过。检查容器禁网、不接设备和个人配置。此历史计数不等同于最新源码在 Linux 的全回归。

最新本机开发便携包包含 BLE 0.1.4 / USB 0.1.2 与能力示例筛选；中文/空格路径的真实 exe smoke、四板 catalog、独立工具、缺 ADB 与端口冲突检查通过，382 源码 / 9 静态资源 / 16 镜像 / 4 冻结模块与构建快照一致。应用版本 0.1.0、dirty=true，尚非正式 GitHub 二进制 Release；产物与 SHA256 见[便携说明](PORTABLE.md)。

macOS、Linux 原生桌面未验收。2026-10-13 公开源码提交 `0097e23` 的 [GitHub CI run 38384089654](https://github.com/shenlan-ai/esp32-android-agent/actions/runs/38384089654) 在公开后重试成功：10 个 job 全部通过，Ubuntu/Windows × Python 3.10/3.12 各 300 服务端测试、无 skip、1 依赖 warning，另有 5 网页测试、四板构建、59 工具测试及 OpenSpec 治理检查。便携构建工作流尚未远程运行。最新状态查看[Actions](https://github.com/shenlan-ai/esp32-android-agent/actions)，实际发布核验写入 `prepare-github-publication` 验证记录；该远端证据不能代替其他设备的输入验收。

## 历史问题与未执行项

0.1.1 曾未就绪，0.1.2–0.1.4 初次连接曾缺报告订阅；手机断开/重新配对与主机重绑后恢复。完整备份也曾失败，换主机 USB 口后读取成功；根因未确定，不能由一次成功保证长期可靠。早期 swipe 笑脸失败、模型结束格式失败与旧草稿误输入均保留在[报告](acceptance/2026-10-13-redmi-note14-ble.md)。

其他手机、Android 16/17、S3 实物、旋转/拔线、精细小目标、长期稳定性与全自动原生任务成功率仍未验证。请按[验收清单](ACCEPTANCE.md)补充具体条件，不以 DEMO 的 completed 状态代替实机结果。
