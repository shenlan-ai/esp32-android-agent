## Why

用户将实际开发板接入电脑并要求识别与适配。当前 USB 标识为 CP2102 (10C4:EA60)，Windows 错误码 28 且无串口。需要先恢复官方串口驱动，再以实际芯片信息选择控制路线，不能根据桥接芯片推测板型。

## What Changes

- 记录无刷写的设备识别流程、官方驱动来源与实际识别证据。
- 明确 CP210x USB 桥不等于 ESP32 芯片型号；芯片读取不执行擦除或固件写入。
- 将识别后的芯片、Flash、USB/BLE 能力作为后续固件构建依据。

## Capabilities

### New Capabilities
- `board-identification`: 诊断串口与芯片能力，并区分已确认芯片和无法远程确认的 PCB 商品名。

### Modified Capabilities
无。

## Impact

影响硬件识别工具和文档。驱动与检测输出放在忽略的本地运行目录；管理员安装需 Windows UAC，未获得有效串口前不宣称识别成功。后续具体 HID 适配另立变更。
