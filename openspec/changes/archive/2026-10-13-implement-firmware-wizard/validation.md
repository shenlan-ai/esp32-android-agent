## 执行环境与范围

2026-10-12 至 2026-10-13，Windows x64 / Python 3.12.14，OpenSpec 1.13.1、esptool 5.3.0、PyInstaller 6.16.0、Node 24.21.0。复用四板既有编译产物，未修改固件源码或协议，未再次刷写或打开 COM5。仅本机源码、模拟服务与本地分发包，无 push、发布或外部消息。

## 检查证据

归档前最终完整回归：`python -m pytest server -q` **159 passed、1 skipped、1 warning**；`ruff check server` 和工具/脚本 Ruff 均通过。修改范围42项（新增验证记录），暂存后diff检查通过。

- 实现前及增量后 `openspec validate implement-firmware-wizard --strict --no-interactive` 通过。
- `python -m pytest server -q`：158 passed、1 skipped、1 warning；之后新增“读取核验失败保留备份且不重放”一项，`python -m pytest server/tests/test_firmware.py -q`：28 passed。Windows symlink 权限测试跳过；warning 来自 Starlette/anyio BlockingPortal 弃用。最终完整回归在归档前执行并记录下方。
- `python -m unittest discover -s scripts/tests -q`：41 tests OK。含四板镜像布局、旧 CLI 兼容、真实 worker+fake ROM 的单连接身份校验、全 Flash 备份、同一内存镜像 write/verify、换板/短备份/篡改/掉线不重放及原生固件调度测试。
- `python -m ruff check server`、新工具/脚本使用 `--config server/pyproject.toml` 检查通过；修正了新增文件的 EOF 空行及测试 import 分组。`git diff --check` 通过；暂存后再次检查。
- `node --test server/tests/geometry.test.mjs`：3 passed。
- `python scripts/check_workflows.py` 与 actionlint 1.7.12 检查两个 workflow 通过。仅便携工作流增加 firmware extra，其权限、产物和手动触发边界不变。
- `python scripts/check_changes.py`：范围检查通过（归档前 41 个实现及元数据文件）。
- 独立源码工具 `python tools/firmware_worker.py diagnose`：固定 esptool5.3.0、`device_used=false`。

## 生命周期、互斥与失败

新增服务测试调用实际 manager/catalog/worker，ROM由内存假设备提供。覆盖四 profile 完整下载及历史重启、false/错误/过期/复用确认、原备份和暂存镜像/manifest篡改、源目录更新后使用私有快照、MAC换板在stub前拒绝、不支持16MB容量、活跃/暂停任务与HID/USB竞争拒绝、过期排队输入重新检查维护标志。HTTP覆盖CSRF、外来串口、多余字段和非严格bool，维护期间动作/选择/控制切换/监听/任务拒绝、手机stop即时返回且不取消写入。取消HTTP响应不取消应用拥有的写入；取消write被拒绝；优雅关闭被取消仍等待写入完成。

工具超时和取消测试实际启动一个测试父进程及其子进程，证明清理该工具树；没有运行 esptool 或接板。stdout/stderr有界消费且整体等待（含输出EOF）受超时限制。完整备份先检查类型/长度，再哈希；失败后不开放写入ticket。后端阶段耗时在本次操作结束后冻结，避免等待用户时增长成为错误操作耗时。

## 浏览器与分发

- `server/tests/firmware_demo.py --port 8892` 临时目录、假串口/ADB/模型，页面始终标DEMO；真实manager/worker+fake ROM。浏览器实走识别→选择esp32dev→完整备份→下载→默认未选确认→勾选→写入→读取校验。
- 写入期间刷新网页后仍显示后台写入，随后校验通过；手机输入明确标未验收。下载文件实际4,194,304字节，SHA256 `8c7631389970cde5de2c18211fd7b0e8f0618c6ea0221542f518ce4336149203` 与UI一致，文件内容为模拟内存，不含实物Flash。
- 中英文与窄屏错误流程检查；viewport请求390×844，实际布局宽375且scrollWidth375，无横向溢出。故障端口提示断线且写入禁用，控制台无error/warn。截图、下载校验记录在忽略目录 `.runtime-local/firmware-ui/`。临时viewport已恢复，DEMO浏览器和服务已关闭，真实8890服务未重启。
- `scripts/build_portable.py --output dist/wizard-review-v3 --source-cache .runtime-local/release-sources` 成功。ZIP 103,524,192字节，SHA256 `96dc6a5c9c0e2e49c5d63c2c6058c94c07e88365fd12e5671aa82f0b11794820`。这是 dirty 审核构建；最终提交后另行生成干净包，结果保存在忽略的构建日志及smoke记录。
- ZIP解压到 `dist/固件向导 验收/`，`scripts/smoke_portable.py <exe>` 通过：完整inventory、独立工具diagnose、四profile目录、真实主程序诊断/网页/API/缺ADB/端口冲突；移除系统Python/ADB PATH，无实物或模型调用。日志 `.runtime-local/wizard-build-v3.log`、`.runtime-local/wizard-smoke.json`。
- esptool完整对应源码固定 `c94e362317498f52bc1b477851a896213341ee92`，包内tar SHA256 `551baa3cc706e60376fbc12ce698ea18b7a45786f1cec66c64d626509cbb6534`，含源码/构建文件/stub/license。工具自身GPL许可、全部实际依赖及Python许可已收集。包装器和共享模块随project.zip提供。
- 第一次审核构建被主程序审计拒绝（冻结器自动收集源码模式的esptool元数据）；调整版本查询后主程序不含esptool/其GPL代码。第二次构建因应用自身可编辑安装元数据被当成外部依赖而拒绝；应用许可已在根目录，排除自身重复dependency收集后构建通过。未忽略第三方许可失败。

## 限制

当前 `adb devices -l` 没有手机。COM5此前授权刷写及12项板上通信的既有证据保持有效，此变更未重复该操作。网页实物识别/全Flash读写、S3实机、Android15/16/17键鼠及真实模型任务仍待验收；模拟与冻结工具diagnose不构成这些证据。GitHub远程CI、Linux/Python3.10矩阵仍未执行；未发布正式包。备份恢复需核实同一硬件并显式覆盖，此版本不自动恢复。
