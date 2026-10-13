# Windows 便携包

本项目提供本地构建的 Windows x64 便携包。当前尚未在 GitHub 发布正式二进制版本；公开源码不等于发布 ZIP 或 GitHub Release。未来正式分发须按 [发布准备](RELEASING.md) 从明确的已提交版本重新构建与验收，不重命名旧 dirty 开发产物后发布。便携程序包含 Python 和网页，不需要安装 Python、Node 或 Arduino。Redmi Note14 5G / Android15的基本键鼠和BLE0.1.4连续笔划已有实机证据；精细坐标、单次全自动原生任务稳定性、Android16/17及S3实物仍未验证，构建和模拟通过不代表所有手机兼容。

2026-10-13最新开发验证包：`dist/windows-0.1.0-continuous-20261013/esp32-android-agent-0.1.0-windows-x64.zip`，104922338字节，SHA256 `0a6f1d90f34f59087681893ced9a0063f43e9dda7393a7c2f48a6cdc38e201b6`，与sidecar一致。包括BLE0.1.4/USB0.1.2连续path/circle与按当前控制器筛选模型示例的实现。应用版本仍0.1.0，release记录HEAD `e317d7687f92a35533654f4a2c1ee4c9af37194d`、dirty=true、Python3.12.14，是本机开发验证包，未在GitHub正式发布。旧vector-model包保留为历史产物，不含以上最新修复。

在新中文/空格路径解压后真实exe smoke通过：完整inventory、诊断、页面/静态/API、缺ADB、端口冲突、独立工具diagnose、四板catalog，PATH排除系统Python/ADB且未使用设备或模型。382个项目源文件与构建快照逐字节一致，9个冻结静态资源、16镜像与当前源码/catalog一致，冻结agent/llm/models/ble完整代码对象与源码一致；主程序未捆入esptool。真实Git暂存区SHA保持不变。验证记录见OpenSpec `refresh-continuous-hid-portable`。本段SHA和结果在构建后补充，包内文档与OpenSpec为构建前快照。

当前经典COM5板已单次刷入BLE0.1.4并读取校验，通过Redmi Note14 5G / Android15竖屏531/1176校准、闭合path/circle和第二段中途停止释放。本机白板VLM笑脸独立最终核验通过；原生hello由模型新建并输入后，创建任务结束失败，经人工退出和单独VLM任务确认新内容已保存。不能称单次全自动稳定通过或全机型兼容。完整记录见 [手机验收报告](acceptance/2026-10-13-redmi-note14-ble.md)。未来覆盖固件仍需新完整备份及版本明确确认。

## 解压与启动

1. 解压整个 ZIP，保留 `esp32-android-agent.exe` 旁的 `_internal`、`licenses`、`sources`、`firmware`、`tools` 等目录。
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

`firmware/manifest.json` 记录经典 ESP32 4MB BLE、S3 DevKitC-1 N8、XIAO ESP32S3、S3 Zero 4MB 的芯片、Flash、分区和镜像 SHA256。串口芯片识别不能确定商品 PCB 名称。经典 ESP32 不支持原生 USB HID，不能刷 S3 镜像。**运行或解压便携包不会刷写设备。**

网页展开“ESP32 HID 控制 → 安装或更新开发板固件”，先停止任务、切到 ADB 控制，再选择电脑串口。按顺序识别、选择匹配配置、完整备份并下载、勾选覆盖确认、写入并校验。确认限时 5 分钟且只使用一次；过期或失败后需重新识别、备份，不自动重试。S3 8MB 必须按实物标记选择 DevKitC 或 XIAO，未支持容量不会开放写入。识别会复位板子；不加载 RAM stub，不写 Flash。

原 Flash 备份在用户数据目录的 `firmware-backups` 中，带 SHA256 和元数据；可能包含原程序的密钥，应保留且不要公开上传。写入期间保持 USB 和供电，手机 Esc/停止及网页关闭均不会取消写入；Ctrl+C 优雅关闭会等待它结束。强制结束进程或拔线可能使板子无法启动，完整备份可在核实同一设备和容量后用 esptool 从地址 `0x0` 恢复；恢复也是一次覆盖操作，网页不会自动恢复。校验成功只证明镜像，手机输入需继续 BLE 配对或 S3 配网并手动验收。

`tools/firmware-tool/firmware-tool.exe` 是使用固定 esptool 5.3.0 的独立 **GPL-2.0-or-later** 工具进程，主应用不导入 esptool。工具目录含自身 GPL 许可、实际依赖许可与版本；完整 esptool 对应源码在 `sources/esptool-5.3.0-sources.tar`，包装器及共享模块源码在 `sources/project.zip`。主应用的 MIT 许可不覆盖此独立工具；整个分发包包含多种许可。

`release.json`、`requirements-installed.txt` 和 `checksums.json` 提供实际运行依赖、构建版本和全部产物校验；`licenses` 包含依赖和 Python 许可。应用自身 MIT 不代表依赖全部 MIT。PyInstaller GPL 有生成程序的许可例外，Arduino core 使用 LGPL 及组件各自许可。

`sources/project.zip` 是本项目构建时的已跟踪源码；第三方源码 tar 固定官方 tag/commit，校验见 `release.json`；`firmware-relink.zip` 提供四个固件的对象、库、ELF与map，便于替换 LGPL 库重新构建。重建使用项目 PlatformIO 的固定依赖与 `docs/DEVELOPMENT.md`。ESP-IDF SDK 与工具链由 PlatformIO 官方包获取，版本记录在 `hardware/*/platformio.ini`；可分别参考 [Arduino core 2.0.17](https://github.com/espressif/arduino-esp32/tree/2.0.17)、[ESP-IDF 4.4.7](https://github.com/espressif/esp-idf/tree/v4.4.7)、[Espressif 工具链](https://github.com/espressif/crosstool-NG)。正式再分发前还需复核所有组件的声明和发布条件。

## 贡献者构建与验收

在 Windows x64、Python 3.10–3.14 的源码检出中：

```text
python -m pip install -e "./server[dev,build,firmware]"
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

smoke 对照完整 `checksums.json`，然后移除系统 Python/ADB 路径，用隔离目录启动真实 exe；验证独立工具 diagnose、四板目录、页面、静态资源、API、缺 ADB 错误及第二进程端口冲突，结束后关闭测试进程。应在添加 Platform Tools 前运行，因为额外文件会被检查拒绝。此过程不调用模型、串口或真实手机，也不能替代实机任务验收。

GitHub中的 `Build Windows portable artifact` 工作流可手动触发以上构建与解压验收，通过后保留ZIP和SHA的artifact 7天，不发布Release。该配置已在本机通过语法和等效命令检查，首次远程运行仍待验证；不会因存在此workflow就自动生成正式版本。
