# Validation

2026-10-14，Asia/Shanghai。

- 实现前阅读AGENTS.md、console-presentation正式规格、活动列表；变更严格校验通过，skip_specs纯文档/媒体。
- MCP只读status和screenshot确认手机已停在闹钟列表，07:30只响一次且开启；没有输入或修改闹钟。
- computer-use截图当前8890 English工作区。完整页面截图出现布局异常，未采用；使用默认视口getScreenshot获得正常950×870画面，最终图片已视觉检查。
- 仅遮盖BLE设备标识(357,128,475,153)，输出console-workbench.png；前端、手机预览、任务状态、紧急停止保持真实。
- 两份README alt/caption及图片来源同步改为闹钟列表，媒体路径不变，原OpenSpec归档未修改。
- Python/Pillow检查尺寸、两份README本地文件目标、图片引用及闹钟说明通过。初次临时检查把#fragment当文件路径失败，修正为分离fragment后通过，非文档链接错误。
- git diff --check通过（已有LF/CRLF提示）；python scripts/check_changes.py通过；当前变更严格校验通过。
- 本次仅图片及文档，未运行产品测试或固件构建，未提交/推送。完成后归档并复核正式规格与范围。
