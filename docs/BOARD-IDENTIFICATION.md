# 连接开发板的识别

识别先看 USB 桥与驱动，再读取 ESP 芯片和 Flash。USB 桥不能确定商品板型，也不能证明原生 USB HID 能力。

当前连接证据（2026-10-12）：

- USB：CP2102 USB to UART Bridge Controller，VID 10C4 / PID EA60。
- 初始 Windows 状态：错误码 28，驱动未安装，无可用 COM 口。
- 安装 Microsoft Update Catalog 官方签名驱动 11.5.0.417 后：COM5，错误码 0，服务 silabser。
- ESP 主芯片：ESP32-D0WD-V3，revision v3.1；双核 240MHz，40MHz 晶振，支持 Wi-Fi 和蓝牙。
- Flash：4MB；Flash ID 厂商 c4 / 设备 6016，3.3V。
- PCB 商品名：串口信息无法确定；固件使用通用经典 ESP32 配置，无需猜测 DevKit 商品名。

以上芯片和存储信息由 esptool 5.5.0 在 COM5 上读取，并使用 `--no-stub` 复核。当前板子没有原生 USB HID，适配方向为 BLE 键鼠。当前没有刷写固件，也没有进行手机蓝牙验收。

驱动来源为 [Microsoft Update Catalog](https://www.catalog.update.microsoft.com/Search.aspx?q=CP210x)，更新 ID `34213758-173c-47ec-951d-16b2c9463881`。下载 CAB SHA256：`7EA8A03769A05C7BB78718C360B5079BE354ED6437623408D51B9C1E8F5A122A`；CAT 验证结果 Valid，签名者为 Microsoft Windows Hardware Compatibility Publisher。驱动通过正常 Windows UAC 和 pnputil 安装。

CP210x 驱动使用 [Silicon Labs 官方页面](https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers) 或 Windows 官方驱动更新。不要根据 CP2102 直接刷 S3 固件。

恢复驱动后执行：

```text
python scripts/identify_board.py
python scripts/identify_board.py --port COM3
```

识别调用 esptool 的 chip-id 和 flash-id；可能短暂复位设备，不执行擦除或写入 Flash。

ESP32-S3/S2 支持原生 USB HID；经典 ESP32 需要蓝牙 HID。C3/C6 的 USB Serial/JTAG 不等于可编程 USB HID。具体商品板型需要额外可靠资料，芯片信息只用于选择构建目标。
