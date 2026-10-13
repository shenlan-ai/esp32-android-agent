# 验证记录

实现前已读取AGENTS.md、正式portable-distribution/project-governance以及当前活动轨迹变更和上次便携归档。当前板未获BLE0.1.3刷写确认；本变更不访问设备或模型。待执行严格校验、真实打包与解压验收，未勾选任务。

实现前strict通过。首次构建主程序冻结成功，但整进程继承项目临时索引，导致上游源码的只读git diff使用错误索引而拒绝；同时该错误diff的非UTF8内容触发reader警告。未生成ZIP，失败目录保留，没有绕过上游完整性检查。真实索引SHA前后一致，358个允许源码路径均存在。先修订设计，随后重新strict，再采用仅source_archive期间的临时环境包装，在-r2新目录重建。

## 构建与真实解压验收

用Python导入现有scripts/build_portable.py并调用build，原source_archive的调用期间临时设置GIT_INDEX_FILE，finally恢复；传入新输出dist/windows-0.1.0-vector-model-20261013-r2和既有.runtime-local/release-sources缓存。构建成功，ZIP104831789B，SHA256 `08f94d4114dfb4527442d8bf235c3991be7e0d5a3ee90b0cb8e3c771c3f33d31`与sidecar一致。release.json记录0.1.0、HEAD e317d7687f92a35533654f4a2c1ee4c9af37194d、dirty=true、Python3.12.14，ADB未随包提供。真实索引SHA前后均为61c536fce363cbee12b6bb4152cb9bc8034545f9389cff6b4492ac44bcfb0a41，没有创建提交或修改暂存内容。

解压到新目录`.runtime-local/便携 验收/vector-model-20261013-r2`。`.venv/Scripts/python.exe scripts/smoke_portable.py <解压exe>`退出0，inventory、diagnostics、static_and_api、missing_adb、port_conflict、firmware_tool_diagnose与four profiles均通过，system_python_and_adb=excluded、phone_or_board_used=false。原始证据为ignored vector-model-portable-build-r2.log、vector-model-portable-smoke.json和vector-model-index-check-r2.json。

独立内容核对：project.zip的全部358文件与构建时工作树逐字节一致，包括模型修复/联合测试、共享插值实现/C++回归和两个示例fixture；无参考检出、runtime或原Flash备份。5冻结静态资源逐字节一致；manifest四配置与新catalog一致，16镜像逐个长度/SHA通过。使用PyInstaller CArchiveReader读取解压exe嵌入PYZ，两模块android_agent.llm/android_agent.agent的完整代码对象（字节码、递归常量、名称/变量/自由变量、参数与flags）与当前源码optimize=0编译结果一致；主应用PYZ没有esptool/reedsolo/intelhex。原始记录为ignored vector-model-portable-content.json。

仓库文档在实际成功之后补充SHA/结果；ZIP中的文档和OpenSpec是构建前快照，没有将后补记录冒充包内内容。未改产品源码/依赖，未重复最近已通过的两Python完整服务端、工具及四板编译回归；此次证据聚焦真实交付产物。新BLE0.1.3尚未刷入，精细坐标与VLM两case的完整闭环、Android16/17及S3实物仍未验收；无模型请求、手机输入或Flash写入。仅本维护变更可归档，轨迹实机变更仍保持活动。

归档前本变更与preserve-hid-motion-vector strict通过，`python scripts/check_changes.py`163修改文件范围通过，`git -c core.safecrlf=false diff --check`通过。全部本维护任务完成；归档后再次校验正式规格及范围。
