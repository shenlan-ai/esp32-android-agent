# 验证记录

环境：2026-10-12，Windows11 10.0.26200 x64，Python3.12.14、PyInstaller6.16.0、hooks2026.8、PlatformIO6.1.19、Node24.21.0、OpenSpec1.13.1。

- 实现前/后 `openspec validate build-windows-portable --strict --no-interactive` 通过；`scripts/check_changes.py` 范围检查通过。
- `pytest -q server/tests`：131通过、1跳过、1warning。跳过是Windows文件symlink权限；warning来自Starlette TestClient对anyio接口的弃用。新增启动器5项覆盖路径优先级、独占端口、密钥不进入诊断及浏览器启动条件。
- `unittest discover -s scripts/tests` 首轮26项通过；新增加上游源码与许可归属检查后 `test_release_tools.py` 共9项通过（工具套件共28项），包含真实git测试仓库及真实共享固件g++22场景。
- Node坐标3项通过；Ruff服务端及新增工具/打包入口通过。
- `collect_firmware.py --output .runtime-local/release-firmware-check` 验证并收集四板。firmware.bin SHA256与此前真实构建一致：经典 `86f9b27a01b45a5fdd1a609882f8ec0959b3a01260c85f7a87a0b48d886c044c`；DevKitC `854c23eda56c822134b7bce530f5f00c7c0b20d47230ffe123f73e56b91734eb`；XIAO `1eac2c7c300e02f31e46fb0d4b860ccebc41732ac16ea76448856cdf67cf5bdb`；Zero `9f3fdc284f56fe10b0b5ae3b871f7cbd1f21dbf21b124c92c46f5332a164997a`。
- 真实构建：`build_portable.py --output dist/windows-portable-check-5 --source-cache .runtime-local/release-sources`。ZIP 75819474字节，SHA256 `1965e0cdd8ba290f27d8b3d700afe7bc42a820f7157319261fc7db3ce995e0a0`。记录dirty=true的开发快照，完整来源/许可/固件清单随包；没有将原Flash备份、参考检出、个人配置和凭据加入ZIP。
- 解压到 `dist/便携 验收 5`，`smoke_portable.py`真实exe子进程通过inventory、diagnostics、static/API、missingADB和portConflict。PATH仅System32，临时中文data目录，明确缺失ADB绝对路径，无手机/板/模型调用。输出 `.runtime-local/portable-smoke-5.log`，构建日志 `.runtime-local/portable-build-5.log`。
- 首轮发现pyserial wheel缺许可证，构建按要求拒绝；补固定官方v3.5 commit源码/许可。git archive在partial clone会预抓全SDK，已停止该构建下载树，改为核对commit+clean状态后导出选定tracked源码；新增测试证明SDK不进入归档。中文管道输出首次非UTF8失败，便携入口修正UTF8后真实验收通过。开发依赖 `_pytest` 被optional hook引入，已显式排除并检查最终清单。

构建warning包括缺tzdata（产品不调用时区数据库）及macOS串口系统库（Windows未使用该后端）。未实机验证Android输入、S3 HID或供应商模型；本次没有覆盖COM5。包尚未发布/签名，正式外部再分发前仍需许可和实机复核。CI和刷写向导不属于此变更。
