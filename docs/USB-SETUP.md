# ESP32-S3 原生 USB 控制

S3 插入手机 OTG 口作为相对鼠标和键盘；电脑通过 Wi-Fi 控制板子，通过**无线 ADB**获取画面。无需安卓伴侣 App、Root 或板上的模型。当前 COM5 是经典 ESP32，继续使用 [BLE 路线](BLE-SETUP.md)，不能刷入 S3 固件。

## 板型与接口

| PlatformIO 环境 | 明确配置 | 接口 |
|---|---|---|
| `esp32_s3_devkitc` | DevKitC-1 N8，8MB Flash | 标记 USB 的原生口；UART 口不能输出 HID |
| `xiao_esp32s3` | XIAO ESP32S3，8MB Flash | 原生 USB-C |
| `esp32_s3_zero` | ESP32-S3 Zero，4MB Flash | 原生 USB-C；通用 S3 配置，无 LED/GPIO 依赖 |

配置使用 DIO Flash、Arduino 2.0.17、TinyUSB HID + CDC，不依赖 PSRAM。其他 Flash 容量或仿制板需先核实。构建和协议模拟不证明某台手机兼容，实机状态见 [兼容表](COMPATIBILITY.md)。

## 配网与绑定

首次安装可先用 [网页固件向导](PORTABLE.md) 识别、选择配置、完整备份、明确确认并刷写。8MB S3 按实物标记选择 `esp32_s3_devkitc` 或 `xiao_esp32s3`；4MB S3 选择 `esp32_s3_zero`。仅芯片名称不能证实 PCB。首次 ROM 下载按厂商 BOOT/RESET 步骤，使用可下载的 USB/UART 接口；刷写后配网与手机 HID 必须使用原生 USB 口。写入固件和写入网络配置是两个独立步骤。

1. 在网页完成无线 ADB 配对、连接，选择标记 `wireless` 的手机。USB HID 模式拒绝 USB ADB 设备。
2. 将已刷本项目 USB 固件的 S3 **原生 USB 口**接到电脑，展开“ESP32 HID 控制”，刷新并选择串口。首次烧录或端口不可见时，参考板子官方 BOOT/RESET 步骤。
3. 展开“S3 原生 USB 配网”，填写 **2.4GHz** Wi-Fi、密码和电脑局域网 IPv4（如 `192.168.1.20`）。不能填 `127.0.0.1`：它在板子上指向自身。开放网络密码留空；有密码网络使用 8–63 UTF-8 字节，SSID 最多 32 字节。
4. 点击“写入 S3 配网”。主机读取并检查固件身份后才写入；网络参数和每板随机配对密钥保存在 NVS，改网络无需改源码或编译。
5. 配网自动开启板子 TCP 监听，默认 `8891`；网页仍在 `127.0.0.1:8890`。仅在可信局域网使用，在 Windows 防火墙允许板子端口的专用网络入站。访客网络隔离会阻止连接。
6. 将板子移到手机 OTG 口，必要时在手机设置开启 OTG。等待“板子身份已验证”，确认板子插入当前手机，再点击“使用 S3 USB 控制”。这一步不自动点击。
7. 测试鼠标水平/垂直计数，再保存校准。测试只移动。校准按板子、手机 ADB 标识和截图尺寸保存，与 BLE 独立；无线调试地址变化可能改变标识，届时需重新校准。
8. 手动验收点按、拖动、长按、ASCII 输入和紧急停止，再运行模型任务。USB 枚举只表示有主机接入，不能识别手机或证明输入达到预期。

关闭板子监听后控制模式保持 USB 且不可用。再次启用并等板子连回后，**显式重新绑定**才恢复，旧动作不重放。服务重启恢复已启用监听和凭据，控制器仍需重绑。

更换板子端口使用 `--usb-port` 或 `ANDROID_AGENT_USB_PORT`，随后重新给板子配网。`ANDROID_AGENT_USB_HOST` 控制独立监听地址，默认 `0.0.0.0`，无需改变网页地址。首版每个服务配对一块 USB 板子，新配网替换旧配对关系。

## 源码构建

便携包包含四板镜像和独立刷写工具，尚未正式发布。贡献者源码构建：

```text
python -m pip install platformio==6.1.19
python -m platformio run -d hardware/usb_bridge
```

输出在 `hardware/usb_bridge/.pio/build/<环境>/`。固件不包含网络秘密。刷写前识别芯片、Flash 和接口并完整备份；`scripts/flash_board.py` **仅处理经典 ESP32 4MB BLE 固件**，不要用它烧 S3。覆盖现有程序需要用户明确确认；本次没有刷写 S3 实物。

## 结果与恢复边界

随机挑战 HMAC-SHA256 避免在网络上发送配对密钥，TCP 没有 TLS，认证不等于加密传输或抵御中间人。板子不接收手机截图或模型密钥。

`accepted` 表示接收；`done` 表示 HID 报告完成，手机结果仍须截图核验。USB 不提供未实测的 Home/Back/Recents 或音量映射，能力为点按、滑动、长按、滚动、ASCII、基础按键和等待。

停止、断网、USB 断开和心跳失效清空动作并释放键鼠。USB 报告失败时重试中性释放，释放完成前拒绝新动作。手机已拔出时只能清理板子状态，不能确认手机收到释放。动作超时关闭网络并报告结果未知，恢复后先观察，禁止盲目重试。

串口存在但固件无响应时，先检查接口、供电和 BOOT 状态，再尝试 RESET 或只读识别工具复位。当前经典 COM5 的一次回归出现无响应，只读识别复位后全部通信检查恢复；原因尚未确定，没有为此重刷。该现象不构成 S3 实机证据。

## 无设备开发

`python -m pytest server/tests/test_usb.py server/tests/test_provision.py -q` 测试本机 TCP 和模拟 CDC。网页 fixture：`python server/tests/usb_demo.py`，打开 `http://127.0.0.1:8892`。页面标有 DEMO，板子端口仅本机 `8893`，不打开真实串口、不调用真实 ADB 或外部模型，填虚构 Wi-Fi 数据即可。验收后关闭模拟服务。
