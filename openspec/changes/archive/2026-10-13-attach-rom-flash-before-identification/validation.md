## 软件验证

- Python3.12.14与3.10.21：`python -m unittest discover -s scripts/tests`，均43项通过，包含真实共享C++调度器27场景。
- `python -m ruff check --config server/pyproject.toml tools/firmware_worker.py scripts/tests/test_firmware_worker.py`：通过。未使用项目配置的默认全局Ruff另报既有风格规则，不将其当作项目配置下通过。
- `openspec validate attach-rom-flash-before-identification --strict --no-interactive`：通过；新增有限读取超时需求在实现前再次strict通过。
- `python scripts/check_changes.py`：通过，38个修改文件。

## 实机证据

- 当前COM5真实芯片ESP32-D0WD-V3 rev3.1；初始化SPI接口后识别4194304字节，只列esp32dev，不猜商品板型。
- 首次正式备份失败，未开始写Flash。只读诊断显示直接API连接缺少有限串口读取超时；有限超时探测stub启动成功。
- 诊断完整备份已读出4194304字节，文件长度与工具结果SHA256核对一致，保存在本机忽略目录。诊断文件不作为向导覆盖ticket的依据。
- 正式生产向导重新识别与完整备份成功，phase=ready；实际文件4194304字节且SHA256与向导元数据核对一致。只读备份未执行Flash覆盖；本次镜像覆盖确认属于独立的BLE节奏变更。

本变更完成真实识别与生产备份流程，未证明所有驱动或板型兼容，也不证明手机输入精度。原始诊断、备份和设备标识留在`.runtime-local/phone-acceptance/`及`firmware-backups/`，不提交。
