# 验证记录
实现前已读取AGENTS、正式project-governance/continuous-validation/portable及活动状态（无活动）、上游README/NOTICE/MIT。当前远端无配置，本地main/HEAD e317d76有历次已归档实现修改。目标GitHub仓库存在、私有且空；gh已登录并有repo/workflow权限。用户明确答复“改为公开开源，推送后通知我”。尚未修改公开状态或推送。
## 文档、素材与隐私检查（2026-10-13）
- 中英文 README 对齐真实案例与边界；新增 SECURITY、RELEASING 和两张图片及来源说明。使用生产浏览器 UI 收起设置、刷新连接，不运行手机输入或新模型任务；工作台图片裁切并不透明遮盖设备标识，手机案例图仅裁切/缩放与外部事实标签，视觉检查通过。
- `gh api markdown --method POST -F text=@README.md -f mode=gfm -f context=shenlan-ai/esp32-android-agent` 及英文文件使用 GitHub GFM 渲染；本机隔离预览中两图片均 complete、自然尺寸正确，3 个表格可读，首屏和案例排版检查通过。Mermaid 的真正 GitHub 动态渲染留待推送后核验，本机 API fragment 仅保留代码。
- Python 一次性检查 17 个 Markdown 文件：相对文件链接及围栏错误 0；ignore 20 个正反样例全部通过（凭据、任务、Flash、构建缓存排除，文档图片、源码、示例 env 与 manifest 保留）。
- 一次性隐私检查 393 个当前源码/待提交文件、334 个可达历史 blob，比较本机保存的 2 个凭据值并检查 credential-shaped/private-key/device/provider 标识模式：匹配 0；无大于 2MB 源文件、无禁止的本机数据/参考检出/Flash/ZIP 路径。扫描只输出路径与类别，不打印秘密。该检查不声称能识别任意未知秘密；另人工审视图片和 staged 路径。正常 Git 作者信息保留。

## 本机发布回归
- `.venv/Scripts/python -m pytest -q server/tests`：Python 3.12，299 passed / 1 skipped / 1 warning，32.98s。skip 为 Windows 文件 symlink 权限；warning 为依赖弃用提示。
- `.runtime-local/python310/venv/Scripts/python -m pytest -q server/tests`：Python 3.10，299 passed / 1 skipped / 1 warning，33.32s；同一权限 skip，依赖弃用提示。
- `.venv/Scripts/python -m unittest discover -s scripts/tests`：59 tests OK，16.821s，包含真实共享 C++ 固件编译执行；命令输出中 argparse 拒绝缺覆盖确认是预期测试。
- `.venv/Scripts/python -m ruff check --config server/pyproject.toml server scripts tools packaging`：全部通过。
- `node --test server/tests/geometry.test.mjs server/tests/board-status.test.mjs`：5 passed，0 skip。
- `.venv/Scripts/python scripts/check_workflows.py`：只读权限、固定 Actions、无设备与产物约束通过。
- `.venv/Scripts/python -m platformio run -d hardware/ble_bridge`：esp32dev SUCCESS，程序1137817B / RAM39380B。
- `.venv/Scripts/python -m platformio run -d hardware/usb_bridge`：三 S3 配置 SUCCESS；DevKitC/Zero 程序738321B / RAM56984B，XIAO程序724773B / RAM56536B。没有刷写。
- `openspec validate --all --strict --no-interactive`：16 正式规格 + 本变更共17 passed；`openspec validate --archived --no-interactive`：35 passed。
- `.venv/Scripts/python scripts/check_changes.py`：208 修改文件范围通过。`git -c core.safecrlf=false diff --check`：通过。

## 限制与待完成发布操作
本次不重复设备操作或付费模型请求、不重建二进制、不创建 Release。手机实测沿用实际报告，其他手机/系统/S3/旋转/拔线未验证。GitHub 远端检查、推送与公开状态将在实际完成后补充；尚未称远端 CI 通过。
## 暂存与首次 push 基线检查
- 以全部零 before SHA 运行 `scripts/ci_base.py --event push --before 0000000000000000000000000000000000000000` 得到真实空树；`scripts/check_changes.py --base 4b825dc642cb6eb9a060e54bf8d69288fbee4904`：393 文件范围通过，符合首次 GitHub push 检查条件。
- 明确项目文件/目录 `git add -A` 收集最终工作树，移除旧暂存的已归档活动变更残片。208 个 staged 文件只含项目源码/文档/规格；唯一活动目录为本准备变更，两图片与来源说明已纳入。
- `git -c core.safecrlf=false diff --cached --check` 与 `git diff --exit-code` 通过。远端在提交前再次确认 PRIVATE、isEmpty=true；没有需要覆盖的远端历史。
## 实际公开与远端验证
- 发布提交 `0097e23412d2528b09dd052a4035d97e25c8539d`：208 文件，关联20个OpenSpec变更。添加指定 HTTPS origin 后无 force push 到 main；`git rev-parse HEAD` 与 `git ls-remote origin refs/heads/main` 同 SHA。
- 按用户“改为公开开源，推送后通知我”执行 `gh repo edit shenlan-ai/esp32-android-agent --visibility public --accept-visibility-change-consequences`，CLI 与真实网页均确认 PUBLIC、默认 main。补 About 一句话事实描述和7个匹配主题，未改变其他权限。
- 无凭据 HTTP 检查：仓库、两 README 与两图片均 HTTP 200，raw 内容与本地一致。GitHub 真实页面两图 naturalWidth/Height正确、complete=true，三表格及 Mermaid 架构图实际渲染通过；未上传原始图片/配置。
- `Continuous validation` run https://github.com/shenlan-ai/esp32-android-agent/actions/runs/38384089654：首次 attempt1 在私有状态下0步骤，被GitHub账户计费限制拦截，不是源码测试失败。仓库公开后仅重试一次（`gh run rerun ... --failed`），attempt2 completed/success，全部10个job成功。
- 远端日志实际证据：Ubuntu/Windows × Python3.10/3.12各300 passed、0skip、1依赖warning；全源码Ruff与CI base测试通过；Node22五项网页测试、四板构建、59工具测试及真实共享C++、17活动+正式检查/35归档检查、首次push空树范围检查均成功。首次远端证据已写入贡献/开发/兼容说明，并加真实CI状态徽章。
- 不创建Tag、GitHub Release或上传旧dirty二进制包；portable工作流未远程执行，继续明确标待验证。没有发送外部通知，最终仅在本聊天通知用户。
- 归档前所有任务完成；归档只处理本变更，正式规格不变。归档证据随后作为第二提交推送，再由工具核对最终SHA/clean与新的CI状态，不事后修改归档历史。
