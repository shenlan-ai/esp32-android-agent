# 验证记录
实现前读取AGENTS、正式agent规格与最新实机记录；continuous变更已完成有限复测并归档。旧ACT_PROMPT直接列不可用导航与伪动作示例为静态证据。只读实际探测返回合法tap，不执行、不据此判定所有历史协议错误根因。

continuous归档前普通git diff --check此前通过；末次误用core.autocrlf=false使既有CRLF显示为trailing whitespace，输出为假阳性。恢复仓库实际Git配置后diff检查退出0；未进行无关换行重写。

## 软件检查
Python3.12全部服务端299 passed/1 skipped/1依赖弃用warning，33.45s；Python3.10同299/1/1，34.97s。Windows symlink权限项跳过。新增4场景从实际TaskRunner捕获ADB、已校准HID、未校准HID请求；空能力start零模型调用提前拒绝，并独立检查提示仅含元决策。每个示例通过现有严格parse_decision，独立goal_check false仍任务failed，零设备输入。

首轮测试正确暴露空能力不能启动的门禁，修正测试预期并在设计中明确，不修改产品门禁。最后仅导入排序调整，全源码Ruff通过；需要再跑针对性agent测试。源码提示修复未修改模型配置、预算、严格解析或固件。服务重启前释放COM5，核对自有8890服务身份后关闭并Hidden重新启动；重新绑定同一手机/COM5及原0.1.4有效校准，hid_ready=true。

## 能力示例筛选后原生hello保存核验（2026-10-13）

OpenSpec scope-model-action-examples修复提示中同时列不可用ADB导航和home|back|recents伪动作的问题。每次只列当前控制器支持的合法示例，done/fail/replan始终提供并禁止输入字段；不修改严格解析/核验/模型预算。不能据此确定所有旧非法响应的单一根因。Python3.12/3.10各299通过、1 Windows symlink权限skip、1依赖warning；最终导入整理后agent针对性23通过，全源码Ruff通过。

生产重启前释放输入及COM5，重启后重绑同一经典0.1.4板，BLE四项就绪及531/1176竖屏校准有效。手动BLE退出新笔记后，稳定列表显示新hello 17:23与旧hello 6:04，证明新增内容已保存；没有再次创建或输入。自然语言仅核对新笔记的任务133.03秒、12模型调用、29237真实tokens、3次tap。第一次独立goal_check因只看详情无法确认新旧身份而拒绝；模型返回列表观察时间，再打开最新条目。最终独立goal_check确认标题占位为空、正文hello、5字、17:23，任务completed/hid_release_sent。全部实际动作仅查看，无type/新建/删除。

白板笑脸与原生hello内容均实机达成，保存核验闭环通过；原生创建任务本身仍failed后经人工退出和单独核验完成，不能描述为单次全自动稳定通过或统计成功率。旧草稿误输入/清除、失败记录均保留。其他手机/系统、USB实物、旋转/断线及远程CI尚未验收。原始记录/scoped-prompt-*仅在ignored本机目录。

最后任务/文档检查：strict通过，范围187修改文件通过，git -c core.safecrlf=false diff --check退出0；全部本变更任务完成。未重跑无关固件/工具/网页测试，没有刷写或放宽协议。归档后校验正式规格。
