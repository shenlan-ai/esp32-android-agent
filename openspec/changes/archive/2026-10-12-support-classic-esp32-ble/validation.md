# Validation

2026-10-12，Windows，Python 3.12.14。开发验证完成；尚未刷写或进行安卓手机 BLE 输入验收。

## 自动检查

- `.venv/Scripts/python.exe -m pytest -q server/tests`：54 passed。覆盖串口关联、未知结果不重放、取消/停止、BLE连接与能力、手机绑定和旋转校准拒绝；Starlette/anyio 发出1条弃用警告，无失败。
- `.venv/Scripts/python.exe -m unittest discover -s scripts/tests`：19 passed，无跳过。包含真实固件调度/参数验证代码的原生 g++ 编译运行，22个场景通过；未明确确认刷写的拒绝测试会打印预期 argparse 错误。
- `.venv/Scripts/ruff.exe check server`：通过。
- `node --test server/tests/geometry.test.mjs`：3 passed。
- `.venv/Scripts/python.exe -m platformio run -d hardware/ble_bridge`：esp32dev / 4MB / DIO / min_spiffs 构建成功。静态 RAM 39172/327680（12.0%），程序 1135709/1966080（57.8%）；firmware.bin 文件1142288字节。
- 固件 SHA256：`86F9B27A01B45A5FDD1A609882F8EC0959B3A01260C85F7A87A0B48D886C044C`。
- 实际构建产物通过 `flash_board.images()` 预检：经典ESP32 image ChipID=0，OTA_0 app分区0x10000/0x1E0000。预检发现旧代码误用factory分区subtype，已修正并增加正反测试。
- `openspec validate support-classic-esp32-ble --strict --no-interactive`、`python scripts/check_changes.py`：通过；归档后再次执行全规格与范围检查。

## 真实板与本机

- COM5 读取芯片 ESP32-D0WD-V3 v3.1，双核240MHz、40MHz晶振，Flash4MB，CP2102串口桥。通用esp32dev配置不依赖PCB商品名或GPIO外设。
- 原Flash完整备份：`.runtime-local/firmware-backups/esp32-20261012-193945.bin`，4194304字节；SHA256 `96A8ED454EC2A1D74F480824CE91FDBD8919E22C5AFD98AA55D926BB46F5204D`。备份及校验文件仅本机保存，不提交。
- 本次未执行write-flash；原固件保持。刷写工具默认只备份，写入需明确参数，且重新建立完整备份后才写。
- PlatformIO所需pip缺失已修复并纳入构建文档；工具链与框架下载后校验官方完整SHA256。
- 最新真实服务在127.0.0.1:8890运行，明确指定ADB绝对路径；页面显示COM5可选，当前ADB无手机。

## 浏览器验收

- 独立8891模拟服务通过生产API与静态界面验证：未配对、已配对待校准、保存后就绪、BLE导航键禁用、紧急停止及中英切换。模拟页醒目标明不操作真实板或手机。
- 保存非默认水平800/垂直1200，等待成功反馈后刷新，页面正确恢复800/1200。入口mtime资源版本与no-store解决旧脚本缓存。模拟与真实控制台JS错误日志为空。
- 模拟服务和临时tab已关闭；真实控制台保持打开，截图在忽略目录 `.runtime-local/ble-setup-preview.png`。

## 发布前仍需验收

- 刷入当前板后验证真实串口握手、看门狗和释放行为。
- 真实手机主动配对Android Agent BLE，验证订阅、键鼠输入、坐标校准、拖动时序、停止、断线与旋转。
- Android15/API35、16/API36、17/API37以及各厂商和其他板型目前没有实测记录；模拟与编译通过不能替代这些验收。
- 自动任务实现属于仍活动的implement-verified-agent，不由本变更宣称完成。
