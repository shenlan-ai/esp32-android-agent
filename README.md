# ESP32 Android Agent

本地运行的安卓视觉操作项目：ESP32 通过 HID 操作手机，ADB 获取画面，视觉模型规划与验证任务。经典 ESP32 使用电脑串口 + BLE 键鼠；S3 使用 Wi-Fi + 原生 USB 键鼠和无线 ADB。

同时提供无硬件的 ADB 体验路径。手动连接验证不要求模型账号；自动任务使用用户配置的 OpenAI 兼容视觉模型。

当前处于开发阶段，已实现 ADB 手动工作台和自动任务闭环：规划、单步动作、画面核验、最终目标核验、暂停接管、预算限制及本机记录导出。自动任务通过模拟集成与浏览器验收，真实模型供应商和手机端仍待验收。经典 ESP32 的 BLE 固件已构建并刷入当前板，真实串口握手、停止、看门狗与主机重连检查通过；校准已完成自动测试与模拟界面验证。整体设计见 [架构](docs/ARCHITECTURE.zh-CN.md)。

当前连接板已经实测识别为 **ESP32-D0WD-V3 v3.1、4MB Flash、COM5**。它没有原生USB HID，不能刷参考项目的S3固件。连接、构建与保留原固件步骤见 [BLE 使用说明](docs/BLE-SETUP.md)，验证状态见 [兼容表](docs/COMPATIBILITY.md)。

S3 的 DevKitC-1 N8、XIAO ESP32S3 和 S3 Zero 4MB 固件构建通过；网页提供固件识别、完整备份、确认覆盖和读取校验，再写入网络和配对信息，无需改源码。主机连接、安装向导和配网已模拟验证，S3 实机输入待验收。流程见 [USB 使用说明](docs/USB-SETUP.md)。

## Windows 便携运行

贡献者可构建包含 Python、网页、四板固件和依赖来源的 Windows x64 ZIP，用户解压后双击 exe 启动。ADB 从 Google 官方下载，放在 exe 旁 `platform-tools` 目录；无需安装 Python、Node 或 Arduino。构建、启动和校验见 [便携包说明](docs/PORTABLE.md)。当前产物仅在本机验证，尚未发布正式二进制版本，实机限制见兼容表。

## 源码运行

需要 Python 3.10+ 和 Android Platform Tools（ADB）。手动模式无需模型。

```text
python -m venv .venv
.venv\Scripts\python -m pip install -e "./server[dev]"
.venv\Scripts\python -m android_agent
```

macOS/Linux 使用 `.venv/bin/python`。打开 `http://127.0.0.1:8890`，连接并授权手机，在网页选择设备。

ADB 不在 PATH 时使用 `--adb <绝对路径>`；端口可通过 `--port` 调整，`--diagnose` 查看环境，`--open-browser` 启动后打开页面。无线连接在网页向导中完成，配对地址与连接地址使用各自端口。

确认手动控制正常后，在网页保存视觉模型地址、名称与密钥，点击“测试模型”，再输入自然语言目标。模型测试使用合成图片，任务运行时才上传手机画面到你配置的服务。详细流程、暂停恢复与用量边界见 [自动任务使用说明](docs/AGENT-USAGE.md)。

## 开发

源码模式的网页安装固件功能需要可选的 `./server[firmware]`，以及构建后由 `scripts/collect_firmware.py --output <新目录>` 生成的镜像目录。启动时传 `--firmware-dir <目录>`；便携包已提供工具和镜像，普通用户无需这些命令。完整流程与备份恢复见 [便携说明](docs/PORTABLE.md)。刷写工具是独立 GPL 进程，应用仍为 MIT，分发包包含各组件许可与来源。

- [开发规范](AGENTS.md) / [agent.md 入口](agent.md)
- [OpenSpec 流程](docs/DEVELOPMENT.md)
- [贡献指南](CONTRIBUTING.md)

所有修改通过 OpenSpec 管理。已确认的基线是单手机、单任务、两种控制路径、基础手势、执行验证和人工接管。

## 上游与许可

参考 [esp32-iphone-agent](https://github.com/onehumanbeing/esp32-iphone-agent)，采用 MIT 许可证；移植代码保留原版权声明。来源见 [NOTICE](NOTICE)。
