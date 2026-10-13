## Decisions
使用既有构建器、独立固件工具及.runtime-local/release-sources缓存，在dist/windows-0.1.0-continuous-20261013新目录构建。应用仍0.1.0/dirty=true，四配置为BLE0.1.4/USB0.1.2。

沿用已验证source_archive专用GIT_INDEX_FILE包装：ignored新索引read-tree HEAD，再仅add允许项目根；仅调用source_archive期间设置环境，finally恢复，避免上游Git继承错误索引。真实索引前后SHA一致，不改用户暂存、参考检出或产品脚本。

新包docs/OpenSpec为构建前快照，构建后SHA/结果在仓库补充，明确时序。
## Validation
在新中文/空格目录解压，真实exe smoke覆盖完整inventory、隔离系统Python/ADB、页面/API、缺ADB、端口冲突、独立工具diagnose和四板入口。逐字节核对全部project.zip源文件、5静态资源、16固件镜像及冻结agent/llm/model代码对象；确认包不含参考检出、配置或Flash备份。源码/四板已有适用完整验证，无产品代码变化不重复；strict/范围/diff后归档。
