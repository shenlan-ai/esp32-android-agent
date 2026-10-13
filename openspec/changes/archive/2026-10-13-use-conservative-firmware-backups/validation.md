实现前strict通过。真实COM5两次高速完整备份失败，独立只读诊断确认stub/切速成功，read_flash失败；115200下64KB读取成功（7.5秒）。无Flash写入。

Python3.12.14及3.10.21定向`pytest -q server/tests/test_firmware.py`各28 passed；两环境工具测试各44通过。实际生产worker配假ROM验证高速读取故障条件下低速完整字节及SHA、单次连接、write仍460800；真实manager四profile流程覆盖4MB600秒、8MB1084秒期限。Ruff在server目录通过。完整回归在此小修正前分别216 passed、1 skipped，此修正后的相关测试已通过，没有无理由重复全套。

115200整片备份在386.5秒失败；生产工具将底层异常脱敏，未保留该次原始原因，故不推断最终摘要超时或其他根因。无完成备份、无写Flash。独立末尾256KB只读校验成功，24.9秒。先扩展提案/规格/设计/任务并strict后，向导改为同连接连续256KB读取，保留官方段摘要核验、任一失败即终止。传统CLI改为115200/600秒，write仍460800/180秒。

新增两Python版本工具回归各49 passed；3.12/3.10主机固件相关各28 passed。测试覆盖连续4MB/8MB范围、不同范围字节内容、完整SHA、后续段失败不重连/重读且无输出、CLI真实子进程参数/完整内容散列/失败不write。Ruff通过。范围检查64文件通过；`openspec validate --all --strict --no-interactive`18项、归档17项通过，git diff --check通过（仅既有换行提示）。当前运行服务的4MB期限仍为600秒，与更新后相同；8MB新期限在两版本测试中验证，实际服务需下次重启才加载。其他板型实机、Linux与远程CI未执行。传统CLI新版低速整片实机检查未执行，不能以向导分段检查证明其完整传输可靠。

生产向导新连续分段4MB备份在193.4秒失败，无新完成备份、无写Flash，不归档此变更。COM5仍可识别，最近30分钟System事件中未检出USB/Kernel-PnP/DriverFrameworks记录，这不足以排除供电/线材/驱动问题。失败后生产BLE重新绑定，connected=true、firmware=0.1.1、hid_ready=false，没有执行HID输入。原始失败原因未从工具协议公开，不能将193.4秒当作确定失败地址或宣称分段修复成功。建议更换数据线并直连主机USB口后，在新连接条件下重新验收。

`report-firmware-failure-stages`增加脱敏阶段/计数后，为观察真实故障显式执行一次新生产备份：147.2秒失败，read阶段此前已完整读取1310720/4194304字节，固定类别operation_failed。失败范围内中断位置和根因仍未知，没有完整文件、覆盖ticket或Flash写入。失败后不重复读取；一次RTS复位恢复串口握手0.1.1，但hid_ready=false。第1.3未完成，本变更仍活动；用户尚未确认USB连接条件改变。

2026-10-13用户明确回复已更换可靠数据线并直连USB。先strict验证本变更及diagnose-ble-readiness，再以生产向导重新识别：COM5、ESP32-D0WD-V3 rev3.1、4194304字节，与此前身份一致，仅esp32dev兼容。切ADB仅为串口维护，不发送ADB输入。在新连接条件下仅启动一次完整备份；335.5秒后失败，read阶段此前完整成功3407872/4194304字节，类别operation_failed，无完成备份、无有效覆盖ticket、无Flash写入。不能把时间或已读计数视为失败段内地址，也不能据此确定线材或驱动根因。有效BLE重绑立即成功，无须RTS复位；connected=true、firmware=0.1.1、hid_ready=false，没有手机输入或重复完整读取。含私密身份的状态保存在ignored `.runtime-local/phone-acceptance/new-cable-*.json`。第1.3仍未完成，不归档；进一步请求用户更换主机USB口并核对外接接线。

本轮仅补实机验证证据及说明，未改产品实现或依赖，不新增测试。`openspec validate --all --strict --no-interactive`18项通过、`openspec validate --archived --no-interactive`20项通过、`python scripts/check_changes.py`94文件通过、`git diff --check`通过。未完成的下载SHA核对、0.1.2刷写及手机动作测试没有执行。

2026-10-13用户确认已换主机USB口后，仅执行一次新的生产完整备份。串口仍COM5，识别同一ESP32-D0WD-V3 rev3.1、4194304字节，与此前保存身份一致，仅esp32dev兼容。备份384.3秒完成；下载完整4194304字节，SHA256为a2750e22b790136d60d8b640d5933eb103eba67b37049d163ffb9d5bbe88e22e，与响应X-Firmware-SHA256和记录一致，文件保存ignored本机目录。没有Flash写入；这证明本次新USB条件下完整传输成功，不能确定此前根因或保证长期可靠。BLE0.1.2四个catalog镜像实际长度/散列核对通过，应用BIN1143248字节、SHA256为84d0664dcecce24667e08ee6ce499294eea49399ffd2219c93dabd098578b51f；等待新覆盖确认，手机就绪及坐标仍待验证。

本次仅执行新USB条件下实机验收并补证据，没有修改实现或依赖。strict全部18项通过，check_changes覆盖100文件通过，git diff --check退出0。未重复已通过软件回归；0.1.2覆盖及手机输入尚未执行。保守备份变更的完整下载验收任务现已完成，可归档；BLE分层诊断和手机任务变更仍活动。
