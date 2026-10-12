# Windows 便携包

本项目提供本地构建的 Windows x64 便携包。当前尚未在 GitHub 发布正式二进制版本。便携程序包含 Python 和网页，不需要安装 Python、Node 或 Arduino。Android 与 S3 实机输入仍待验收，构建和模拟通过不代表所有手机兼容。

## 解压与启动

1. 解压整个 ZIP，保留 `esp32-android-agent.exe` 旁的 `_internal`、`licenses`、`sources`、`firmware` 等目录。
2. 从 [Google 官方页面](https://developer.android.com/tools/releases/platform-tools) 下载 Windows Platform Tools，阅读并接受其许可后解压，将完整 `platform-tools` 文件夹放在 exe 旁。ADB **没有随项目便携包再分发**；不要只复制 adb.exe，它还需要 DLL。
3. 双击 `esp32-android-agent.exe`。控制台会显示数据路径和本机地址，服务启动成功后打开浏览器。首次没有 ADB 也能查看工作台；补充工具后重启程序。
4. 手机开启开发者选项和 USB 调试，连接电脑，在手机上授权；网页选择设备。在 ADB 体验模式验证画面与手动控制，无需模型密钥。自动任务配置见包内 `sources/project.zip` 中的 `docs/AGENT-USAGE.md`。

退出时在控制台按 Ctrl+C，等待服务关闭。关闭网页不会停止后台服务。设置与记录默认在用户目录 `.esp32-android-agent`，升级时可换新程序目录，保留此用户目录；不要把它分享给别人。

```text
esp32-android-agent.exe --diagnose
esp32-android-agent.exe --adb "D:\Android Tools\platform-tools\adb.exe"
esp32-android-agent.exe --port 8892 --no-browser
esp32-android-agent.exe --data-dir "D:\My Agent Data"
```

ADB 选择顺序：`--adb`、`ADB_PATH`、exe 旁 `platform-tools/adb.exe`、PATH。诊断不会打印模型密钥或访问令牌。端口冲突时选择不同 `--port`，程序不会接管其他服务。默认仅本机访问，远程访问须显式配置访问令牌。程序没有签名；Windows 可能提示 SmartScreen，运行前核对你信任的来源和 SHA256。

## 固件与来源

`firmware/manifest.json` 记录经典 ESP32 4MB BLE、S3 DevKitC-1 N8、XIAO ESP32S3、S3 Zero 4MB 的芯片、Flash、分区和镜像 SHA256。串口芯片识别不能确定商品 PCB 名称。经典 ESP32 不支持原生 USB HID，不能刷 S3 镜像。此版本包还没有网页刷写向导；经典板用包内源码 `scripts/flash_board.py` 配合 Python/esptool，S3 通用刷写入口另行开发。**运行或解压便携包不会刷写设备。**

`release.json`、`requirements-installed.txt` 和 `checksums.json` 提供实际运行依赖、构建版本和全部产物校验；`licenses` 包含依赖和 Python 许可。应用自身 MIT 不代表依赖全部 MIT。PyInstaller GPL 有生成程序的许可例外，Arduino core 使用 LGPL 及组件各自许可。

`sources/project.zip` 是本项目构建时的已跟踪源码；第三方源码 tar 固定官方 tag/commit，校验见 `release.json`；`firmware-relink.zip` 提供四个固件的对象、库、ELF与map，便于替换 LGPL 库重新构建。重建使用项目 PlatformIO 的固定依赖与 `docs/DEVELOPMENT.md`。ESP-IDF SDK 与工具链由 PlatformIO 官方包获取，版本记录在 `hardware/*/platformio.ini`；可分别参考 [Arduino core 2.0.17](https://github.com/espressif/arduino-esp32/tree/2.0.17)、[ESP-IDF 4.4.7](https://github.com/espressif/esp-idf/tree/v4.4.7)、[Espressif 工具链](https://github.com/espressif/crosstool-NG)。正式再分发前还需复核所有组件的声明和发布条件。

## 贡献者构建与验收

在 Windows x64、Python 3.10–3.14 的源码检出中：

```text
python -m pip install -e "./server[dev,build]"
python -m pip install platformio==6.1.19
python -m platformio run -d hardware/ble_bridge
python -m platformio run -d hardware/usb_bridge
git add <本次已审核的新增源码文件>
python scripts/build_portable.py --output dist/windows-0.1.0
```

输出目录必须不存在；不覆盖旧包，不删除已有目录。构建需要 git 和网络获取锁定的第三方源码；`--source-cache` 可复用已检出的官方 tag。运行依赖记录实际版本，发布重建可从 `requirements-installed.txt` 固定环境。构建源码 ZIP 只包含已跟踪文件的当前内容；新文件先暂存，`release.json` 的 dirty 字段明确是否尚未提交。

将生成的 ZIP 解压到新的目录（建议含空格/中文），然后验收：

```text
python scripts/smoke_portable.py "D:\便携验收\esp32-android-agent\esp32-android-agent.exe"
```

smoke 对照完整 `checksums.json`，然后移除系统 Python/ADB 路径，用隔离目录启动真实 exe；验证页面、静态资源、API、缺 ADB 错误及第二进程端口冲突，结束后关闭测试进程。应在添加 Platform Tools 前运行，因为额外文件会被检查拒绝。此过程不调用模型、串口或真实手机，也不能替代实机任务验收。
