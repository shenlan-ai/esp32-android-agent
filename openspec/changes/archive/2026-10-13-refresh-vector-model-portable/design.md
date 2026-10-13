## Decisions
沿用scripts/build_portable.py、scripts/smoke_portable.py及固定上游缓存，在新的dist/windows-0.1.0-vector-model-20261013-r2构建，不覆盖既有包或第一次失败的输出目录。四配置当前已编译为BLE0.1.3/USB0.1.1，逐镜像核对新catalog与包内manifest。应用版本仍0.1.0，dirty=true。

构建器读取git ls-files并复制工作树内容；当前真实索引包含旧路径的暂存删除状态，直接构建可能遗漏新增源码或读取不存在的路径。使用ignored目录里的独立GIT_INDEX_FILE，read-tree HEAD后只将允许的项目目录/顶层文件add -A。第一次构建让整个子进程继承索引，上游Git只读diff错误比较了项目索引并拒绝构建；没有写上游或真实索引。

修正执行方式：以Python导入现有构建器，仅在调用原source_archive期间通过临时包装器设置GIT_INDEX_FILE，并在finally恢复环境；其余原build逻辑、冻结子进程和上游验证使用原环境，不共享项目索引。环境包装只控制本次命令，不修改仓库脚本或源归档逻辑。开始/结束核对真实Git索引SHA一致，不改变用户暂存内容，不创建commit。不增加运行依赖。

包内文档记录构建前快照，仓库文档在实际smoke成功后补充ZIP SHA和结果；明确后补验证记录不是包内原有内容。新固件为准备镜像，不能将打包成功视为刷入或手机通过。

## Validation
在含中文/空格的新目录解压，运行真实exe smoke：全文件清单、隔离无系统Python/ADB、独立工具diagnose、页面与API、四板入口及端口冲突。逐字节比对关键源码/冻结静态资源和所有固件镜像，确认源码不含参考检出、本机配置、Flash备份；冻结模块提取检查最新模型完成错误与预算处理存在。无需重复无新产品代码的全服务端/四板回归，已有最近真实记录保留。strict、范围及diff检查；全部本变更任务完成才归档，preserve-hid-motion-vector保持活动。
