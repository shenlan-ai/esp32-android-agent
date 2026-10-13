## Decisions
保留现有只读权限、固定Actions和操作系统/Python/四板矩阵；网页job保持原geometry标识以免改变已有必需检查名称。Node命令显式列出两个测试文件，Ruff覆盖四个源码目录。

Ruff命令显式使用--config server/pyproject.toml，检查器同时要求该配置参数；增加移除配置的拒绝场景。Linux工具回归环境必须有Git和g++；源码归档的权限不代表Git检出的权限，避免从ZIP权限推断源码可执行属性。

显式配置仍会按运行目录推断first-party包，因此在项目Ruff配置中声明android_agent为first-party，使根目录和server目录的导入规则一致；不批量重排无关测试。

检查器从每个step的run解析直接命令token，要求node --test包含两个真实路径、python -m ruff check的目标合集包含四目录；注释或另一job中的路径不能冒充覆盖。只检查当前项目明确支持的直接命令，不解析任意shell。

测试在临时目录复制真实两份YAML，分别删除board-status路径、把它移到注释、漏掉tools静态检查及把完整命令移到错误job，确认被拒绝；完整配置通过。无硬件、无付费模型。

Linux回归只使用隔离源码快照和公开依赖，不挂载主机个人配置、串口或Docker socket；容器执行后清理。记录镜像/Python/发行版和实际检查。环境差异产生真实失败时先修正规格/范围再实施，不靠skip冒充通过；远程CI仍未执行。
