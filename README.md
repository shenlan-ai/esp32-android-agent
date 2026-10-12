# ESP32 Android Agent

本地运行的安卓视觉操作项目：ESP32-S3 通过 USB HID 操作手机，无线 ADB 获取画面，视觉模型规划与验证任务。

同时提供无硬件的 ADB 体验路径。手动连接验证不要求模型账号；自动任务使用用户配置的 OpenAI 兼容视觉模型。

当前处于开发阶段，已实现 ADB 手动工作台：设备选择、无线配对、截图和基础输入。自动任务与硬件主模式正在后续变更中实现，实机兼容性待验收。整体设计见 [架构](docs/ARCHITECTURE.zh-CN.md)。

## 源码运行

需要 Python 3.10+ 和 Android Platform Tools（ADB）。手动模式无需模型。

```text
python -m venv .venv
.venv\Scripts\python -m pip install -e "./server[dev]"
.venv\Scripts\python -m android_agent
```

macOS/Linux 使用 `.venv/bin/python`。打开 `http://127.0.0.1:8890`，连接并授权手机，在网页选择设备。

ADB 不在 PATH 时使用 `--adb <绝对路径>`；端口可通过 `--port` 调整。无线连接在网页向导中完成，配对地址与连接地址使用各自端口。

## 开发

- [开发规范](AGENTS.md) / [agent.md 入口](agent.md)
- [OpenSpec 流程](docs/DEVELOPMENT.md)
- [贡献指南](CONTRIBUTING.md)

所有修改通过 OpenSpec 管理。已确认的基线是单手机、单任务、两种控制路径、基础手势、执行验证和人工接管。

## 上游与许可

参考 [esp32-iphone-agent](https://github.com/onehumanbeing/esp32-iphone-agent)，采用 MIT 许可证；移植代码保留原版权声明。来源见 [NOTICE](NOTICE)。
