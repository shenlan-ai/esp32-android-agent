# 当前经典 ESP32 的 BLE 控制

当前连接板已识别为 ESP32-D0WD-V3 revision v3.1、4MB Flash，电脑串口 COM5。商品板名仍未知。CP2102只是串口桥；此芯片没有原生USB HID。

## 连接

```text
电脑 ── USB串口 ── 经典ESP32 ── BLE键鼠 ── 安卓手机
  └──────────────── USB或无线ADB ──────────┘
```

手机不需要安装伴侣App，板子不需要Wi-Fi。蓝牙只用于键鼠控制，ADB负责画面。

## 构建与保留原固件

贡献者在项目根执行（Windows虚拟环境）：

```text
uv pip install --python .venv/Scripts/python.exe platformio==6.1.19 pip==25.3
.venv/Scripts/python.exe -m platformio run -d hardware/ble_bridge
python scripts/identify_board.py --port COM5
python scripts/flash_board.py --port COM5
```

最后一条只备份4MB Flash到`.runtime-local/firmware-backups/`，不写固件。此备份包含原设备配置，保留在本机，不提交仓库或分享。脚本同时写SHA256；恢复可用esptool在地址0写回完整备份，恢复也会覆盖当前Flash，应明确确认。

当前固件PlatformIO目标`esp32dev`，espressif32 6.12.0 / Arduino ESP32 2.0.17、ArduinoJson 7.4.2；DIO、4MB、40MHz Flash、min_spiffs分区。未使用GPIO引脚、板载LED或PSRAM，因此不依赖DevKit特定PCB引脚。刷写前检测必须为经典ESP32和4MB，S3等芯片会被拒绝。

Arduino框架包固定为`3.20017.241212+sha.dcc1105b`，构建用esptool包固定为`2.40900.250804`。uv创建的虚拟环境默认没有pip，构建环境需安装pip供PlatformIO安装工具依赖；普通用户运行控制台不需要PlatformIO。固件协议见 [串口协议](../hardware/PROTOCOL.md)。拖动使用校准时相同的鼠标步幅与节奏，指定时长是按下的最低时长；实际执行时间由板子返回。BLE鼠标操作不提供精确触摸时序保证。

用户明确决定替换原固件后执行：

```text
python scripts/flash_board.py --port COM5 --write --confirm-overwrite
```

脚本先验证构建产物、再创建完整备份，成功后才写bootloader、分区、OTA初始化和app；esptool校验写入数据。此命令会替换原固件，不是芯片识别。

## 配对和校准

1. 板子留在电脑，手机在系统蓝牙设置配对`Android Agent BLE`。若换手机，先在原手机忘记设备。
2. 用USB或无线ADB连接手机，在控制台选择手机并确认画面。
3. 展开“ESP32蓝牙控制”，刷新串口，选板子并点击“使用BLE控制”。未刷入本项目固件会显示连接失败；不会自动改用ADB发送输入。
4. 配对后展开鼠标校准。如果系统允许，关闭指针加速。使用水平/垂直边缘测试（只移动不点击），调整计数到刚好触及对应边缘。过大的数值也会触边，所以应逐渐减小到临界值。
5. 保存当前方向校准，再点屏幕中心和边缘多个位置检查精度。边缘校准不是全屏精度证明；明显偏差时不要运行自动任务。
6. 测试点按、滑动、长按、ASCII输入和紧急停止。旋转或更换手机需重新校准。相同分辨率但指针速度设置变化也需重新校准。

主页、返回、最近任务暂不作为BLE特殊按键提供，因为普通键盘Home不等于Android主页。可点击手机屏幕导航控件。输入按美国键盘布局，中文需要后续可选输入法扩展。

## 状态边界

固件编译通过仅证明当前芯片目标可构建。尚需在当前板上刷写、手机BLE配对、鼠标精度、断线释放和Android15–17各代表机型实测。板子回应done只证明执行完HID报告，手机目标要由画面另外验证。
