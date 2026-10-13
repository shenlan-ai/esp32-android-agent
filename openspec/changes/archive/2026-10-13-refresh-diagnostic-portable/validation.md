## 软件与构建

实现前 `openspec validate refresh-diagnostic-portable --strict --no-interactive`通过；发现两处既有脚本导入排序I001后先扩展proposal/design/tasks/files并再次strict，再用Ruff仅调整导入。两Python版本对server/scripts/tools完整Ruff通过，未修改依赖或产品行为。

- Python3.12.14、Python3.10.21各运行 `python -m pytest -q server/tests`：230 passed、1 skipped（Windows symlink权限）、1 warning（依赖弃用），28.80/29.07秒。日志保存在ignored `.runtime-local/diagnostic-portable-py312-tests.log`及py310对应文件。
- 两环境 `python -m unittest discover -s scripts/tests -q` 各51 passed；导入修正后再次运行均通过。覆盖真实工具main、子进程及固件原生场景，未调用实物或模型。`flash_board`缺确认的argparse报错是预期拒绝用例。
- `node --test server/tests/geometry.test.mjs server/tests/board-status.test.mjs`：5 passed。
- `python -m platformio run -d hardware/ble_bridge`成功，RAM39188B、Flash1136673B；`-d hardware/usb_bridge`三个环境成功，DevKitC/Zero RAM56792B、Flash737429B，XIAO RAM56344B、Flash723873B。没有刷写。

## 真实便携包

新增实现、测试、验收报告及OpenSpec文件先显式加入索引，保证构建源码ZIP包含它们；没有创建commit、push或发布。构建时真实HEAD为e317d7687f92a35533654f4a2c1ee4c9af37194d，不使用早期报告中的旧revision代替；release.json记录dirty=true和Python3.12.14。

`python scripts/build_portable.py --output dist/windows-0.1.0-diagnostics-20261013 --source-cache .runtime-local/release-sources`成功，新ZIP SHA256为102fc966a348b59288e8af30908d11d3a0fb9ac0e5bc49f1fadd4a6c18a07666，与sidecar重新核对一致。使用新目录 `.runtime-local/便携 验收/diagnostics-20261013` 解压；官方来源/许可与对应源码沿用构建器校验，主应用不含esptool。

`python scripts/smoke_portable.py <上述解压目录>/esp32-android-agent/esp32-android-agent.exe`真实子进程通过全部检查：inventory、diagnostics、static/API、missing_adb、port_conflict、独立固件工具diagnose和four profiles；PATH排除系统Python/ADB，phone_or_board_used=false。记录保存在ignored diagnostic-portable-smoke.json。

project.zip中的9个新增/关键源码文件与构建时工作树逐字节一致，包括BLE诊断header及测试、board-status.js及测试、phone fixture、worker/main firmware主机及动作engine；3个冻结静态文件也逐字节一致。不包含参考检出、本机运行目录、Flash备份。经典镜像SHA为84d0664dcecce24667e08ee6ce499294eea49399ffd2219c93dabd098578b51f，与已准备0.1.2产物一致，完整包清单经smoke核验。冻结firmware-tool.exe直接运行无端口backup，code=1，得到严格脱敏validate阶段失败信封，证明新协议确实打包；未访问设备。

文档结果在实际构建/验收之后记录，因此包内文档和OpenSpec是构建时快照；产品源码与镜像未在构建后修改，不能把仓库后补验证记录当作ZIP原有内容。

## 规范与限制

OpenSpec全部/归档strict、修改范围及git diff --check通过；只存在既有CRLF提示。此变更仅完成当前开发包，不归档其他尚未通过的实机变更。

COM5仍BLE0.1.1、connected=true、hid_ready=false，最新完整备份147.2秒失败；用户尚未确认更换USB连接，未再次完整读取或输入。手动精度、长动作中释放、真实模型任务、Android16/17及S3实物、Linux/macOS/远程CI、正式提交发布均未完成。整体goal不能标complete，便携包不能证明这些项目。
