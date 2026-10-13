# 验证记录
已读取AGENTS、正式portable规格、既有维护包design/validation及最新实机报告。continuous与scope提示变更已完成适用软件/手机验证并归档。本变更只交付现有实现，无刷写、模型或设备操作。

## 实际交付检查

新目录dist/windows-0.1.0-continuous-20261013构建成功，ZIP104922338B，SHA256 `0a6f1d90f34f59087681893ced9a0063f43e9dda7393a7c2f48a6cdc38e201b6`，与sidecar一致。0.1.0、HEAD e317d7687f92a35533654f4a2c1ee4c9af37194d、dirty=true、Python3.12.14，ADB未提供。source_archive期间专用临时索引，真实索引前后SHA均61c536fce363cbee12b6bb4152cb9bc8034545f9389cff6b4492ac44bcfb0a41；无用户暂存修改。

解压到.runtime-local/便携 验收/continuous-20261013，真实exe smoke退出0，inventory/diagnostics/static_and_api/missing_adb/port_conflict/firmware_tool_diagnose/four profiles均通过，system_python_and_adb=excluded、phone_or_board_used=false。

源码ZIP382项名称和SHA均等于构建前快照，无参考/runtime/配置/Flash备份。9静态资源（比既有计划5项JS/CSS检查更完整）逐字节与当前源码一致；manifest四profile及16镜像长度/SHA/字节与当前0.1.4/0.1.2 catalog一致。CArchiveReader读取真实exe PYZ，agent/llm/models/ble的字节码、递归常量、变量/名称、参数flags和异常表均与当前源码optimize0编译结果一致；主程序无esptool/reedsolo/intelhex。

原始build/smoke/source-snapshot/index-check/content证据在ignored continuous-portable-*。文档SHA与验收结果在构建后添加，包内文档为构建前快照。不修改产品源码/依赖，无设备、模型、发布或远程CI操作；最新服务端3.10/3.12各299通过及四板编译证据来自前述实现变更，不重复无关检查。

归档前strict通过、范围193文件通过、git -c core.safecrlf=false diff --check退出0。全部维护任务完成，归档后正式规格与范围再次校验。
