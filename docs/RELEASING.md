# 发布准备 / Publication checklist

代码公开与二进制 Release 是两个独立交付。当前提供源码和可手动构建的 Windows artifact，尚无正式二进制 Release。文档不能将本机 dirty 开发包称为正式版本。

所有准备修改遵循 [AGENTS](../AGENTS.md) 和 [OpenSpec 开发流程](DEVELOPMENT.md)，在对应变更中记录实际检查，不事后补空提案。

## 代码公开前

1. 核对 README 中英事实、启动命令、相对链接、真实截图、机型/系统/板型和未验证范围。素材要说明裁切/脱敏，不用 DEMO 冒充实机，不把一次成功称为稳定成功率。
2. 读取暂存与未暂存差异，确认所有修改有变更范围；已归档历史保持不动。检查整个待推送 Git 历史，而非只检查当前目录。
3. 排除模型密钥、Wi-Fi 配置、访问令牌、设备序列号、私人任务导出、原始截图与完整 Flash 备份。仅使用路径或风险类别输出扫描结果，不把匹配秘密打印到日志。核对 `.gitignore` 正反样例；ignore 不会删除已跟踪文件。
4. 保留 MIT 上游来源与版权，检查独立 GPL 工具和依赖声明。参考检出、构建缓存、第三方工具安装和本机产物不纳入源码提交。
5. 执行下面的适用检查，记录结果与 skip/限制。未持有实物不应重复执行设备测试，也不应以模拟结果声明设备通过。
6. 暂存明确的项目文件/目录，检查 staged diff、大小和范围，再提交关联变更 ID。复核远端所有权和现有内容；不使用 force push 覆盖未知历史。
7. 推送后核对本地 HEAD 与远端分支 SHA、公开状态、README/图片可读性、Actions 状态。仓库公开需要用户明确授权；二进制 Release、tag 与外部通知另按实际请求执行。
8. 发布操作完成并记录后，完成任务、归档 OpenSpec、验证正式规格；提交并推送归档证据，再核对最终 SHA。无法完成的任务保持活动，不勾选。

## 无设备回归

以下命令在已安装 `./server[dev]` 的虚拟环境执行；Windows 用 `.venv\Scripts\python`，macOS/Linux 用 `.venv/bin/python`。

```text
python -m pytest -q server/tests
python -m ruff check --config server/pyproject.toml server scripts tools packaging
python -m unittest discover -s scripts/tests
node --test server/tests/geometry.test.mjs server/tests/board-status.test.mjs
python scripts/check_workflows.py
openspec validate --all --strict --no-interactive
openspec validate --archived --no-interactive
python scripts/check_changes.py
git diff --check
```

四板固件需 PlatformIO 6.1.19：`python -m platformio run -d hardware/ble_bridge` 与 `python -m platformio run -d hardware/usb_bridge`。共享 C++ 检查需要 g++ 与构建下载的 ArduinoJson；依赖缺失导致的 skip 不能称为固件回归通过。CI 范围按真实 base 检查，首次 push 使用空树。

## 未来二进制 Release

从明确的已提交 revision 构建，记录版本、dirty 状态、完整依赖、镜像和源码清单；不要重命名旧开发包后直接发布。按 [PORTABLE](PORTABLE.md) 构建到新目录、解压到含空格/中文的新路径、执行真实 exe smoke。核对 inventory、SHA256、独立工具、GPL 对应源码、LGPL 重链接材料与所有组件许可；Google ADB 由用户另外安装。

Release 说明关联 OpenSpec，写清兼容组合、已知限制、实际本地/远端检查，附 ZIP 与 SHA256；不要发布原始备份、密钥或个人日志。网页刷写后的读取校验只能证明镜像，仍需手机端输入验收。

## English

Before publishing, review the complete Git history and staged tree for credentials, device identifiers, private records, screenshots and flash backups. Verify bilingual documentation, image provenance, licenses, OpenSpec scope, software checks and four firmware builds. Push without force, compare local and remote SHAs, then verify visibility and rendered assets.

A binary Release requires a fresh build from an identified revision, extracted-process smoke, checksums, component notices and corresponding sources. A dirty local test ZIP and a workflow artifact are not an official Release. Record actual evidence and pending hardware checks rather than inferring compatibility.
