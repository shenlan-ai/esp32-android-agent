# 验证记录

环境：Windows，Python 3.12.14，Node 24.21.0，OpenSpec 1.13.1，PlatformIO 6.1.19。

## 已完成

- `openspec validate support-s3-usb-hid --strict --no-interactive`：通过，实施前及并发设计更新后均执行。
- `python -m pytest server/tests/test_usb.py server/tests/test_provision.py -q`：34通过。真实loopback TCP用于认证、旧证明拒绝、活跃连接保护、心跳、取消、超时关闭和重绑；CDC使用模拟串口，无物理动作。
- `python -m pytest server/tests -q`：最后完整检查126通过、1跳过、1警告，包含取消配网持久保存匹配凭据和并发模型设置保存测试。
- `python -m unittest discover -s scripts/tests`：19通过，含g++运行真实共享调度/参数验证的22场景。
- `node --test server/tests/geometry.test.mjs`：3通过；`node --check`检查app.js/usb.js通过；Ruff通过。
- 范围检查通过，未修改归档历史或参考检出。
- 归档前 `openspec validate --all --strict --no-interactive`：11项通过；`openspec validate --archived --strict --no-interactive`：7项既有归档通过；`check_changes.py`覆盖30个变更文件，`git diff --check`无空白错误。app.js/usb.js/i18n.js语法最终检查通过。
- 离线网页 fixture `server/tests/usb_demo.py`：验证错误IP拒绝、模拟配网、密码字段清空、手机确认、USB绑定、800/1200校准、英文切换、监听关闭、保持USB不可用、监听恢复后显式重绑及保存校准恢复。页面错误日志为空。
- 截图：`.runtime-local/s3-usb-demo.png`完整1265x2245，`.runtime-local/s3-usb-preview.png`裁剪1265x1650，保留DEMO标记、USB模式、配网、身份和校准状态。仅模拟证据。
- 离线服务与模拟页已关闭。真实8890工作台升级后正常启动，仍识别COM5，未选择手机，USB监听未启用，页面错误日志为空。

## 固件构建

PlatformIO镜像RISC-V包258829021字节下载中断，从官方PlatformIO镜像分段取回，注册表SHA256 `55c5c36593d87021ff19857d99da17a85fe4d708e77333e98ff54a8ac0ed1804` 校验一致，通过PlatformIO包管理器安装保留espressif元数据。首次编译发现缺少tusb.h，补齐后重新运行完整矩阵，最终三个目标均SUCCESS。日志`.runtime-local/s3-build.log`，没有执行upload。

固定依赖：espressif32 6.12.0、Arduino 2.0.17 (`3.20017.241212+sha.dcc1105b`)、esptool 4.9 (`2.40900.250804`)、Xtensa-S3/RISC-V工具链 `8.4.0+2021r2-patch5`、ArduinoJson7.4.2。

| 环境 | 程序/分区B | RAM B | firmware.bin大小B | SHA256 |
|---|---|---|---|---|
| esp32_s3_devkitc | 737277/3342336 | 56784/327680 | 737648 | 854c23eda56c822134b7bce530f5f00c7c0b20d47230ffe123f73e56b91734eb |
| xiao_esp32s3 | 723745/3342336 | 56336/327680 | 724112 | 1eac2c7c300e02f31e46fb0d4b860ccebc41732ac16ea76448856cdf67cf5bdb |
| esp32_s3_zero | 737277/1966080 | 56784/327680 | 737648 | 9f3fdc284f56fe10b0b5ae3b871f7cbd1f21dbf21b124c92c46f5332a164997a |

三个镜像magic=0xE9，chip_id=9(ESP32-S3)均检查通过。未对COM5写入S3程序。

## 当前经典板回归

第一次`check_board_link.py --port COM5`未收到hello，记录在控制台；随后只读`identify_board.py --port COM5`成功再次识别ESP32-D0WD-V3 v3.1/4MB，并由esptool复位。再次检查10项协议与2项生产主机通信全部通过，报告`.runtime-local/s3-change-com5-regression.json`。过程中未刷写，也未发送HID动作；首次无响应的原因未确定，不掩盖该现象或将串口成功视为手机输入验收。

## 实际限制

- 当前只有已刷写BLE固件的经典ESP32 COM5，未再覆盖固件，没有S3实物。
- 无安卓手机或模型配置。S3 USB枚举、真实Wi-Fi、CDC/NVS重启持久性、手机输入和物理断线释放未实测；没有真实任务成功率或Android机型兼容声明。
- Windows无创建文件符号链接权限，现有history导出symlink测试跳过；Starlette TestClient存在既有anyio弃用警告。
- 预编译发布包/通用S3刷写工具和CI另立后续OpenSpec变更；整体goal尚未完成。
