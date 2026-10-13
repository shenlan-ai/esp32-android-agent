## Decisions
沿用现有构建器和锁定工具链，先确认四板产物与当前源代码对应；新增源码纳入Git索引以保证project.zip完整，但不创建提交。产物写入dist/windows-0.1.0-diagnostics-20261013，不覆盖旧目录。复用本机已校验上游源码缓存。

文档明确开发验证包包含未完成实机验收的变更；classic0.1.2为准备镜像，不暗示已经刷入。记录dirty、ZIP SHA和真实子进程验收，实际固件刷写继续受独立规范约束。

## Validation
初次全目录Ruff在check_board_link.py与test_identify_board.py发现I001，仅调整导入分组/排序；先扩展本变更范围并strict，再应用修正。修正后重跑相关工具测试与两版本Ruff，不因格式调整重复全部服务端测试。

两Python版本完整服务端回归及工具测试、Ruff、Node行为测试；四板构建；检查解压后的源码含新增诊断header/JS/测试与本机fixture，检查worker源码及app镜像散列。真实smoke验证无系统Python/ADB、独立工具diagnose、页面/静态资源/API/四板入口和端口冲突。OpenSpec严格、归档及范围检查。实机连接、鼠标精度、长动作释放及模型任务仍待验证，不能由打包证明。
