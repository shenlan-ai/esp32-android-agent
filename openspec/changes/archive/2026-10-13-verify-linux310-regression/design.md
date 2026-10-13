## Decisions
使用官方python:3.10-slim构建独立镜像，安装Git、g++及./server[dev,firmware]；只复制公开源码和固定ArduinoJson以执行共享固件原生测试。记录实际Python、Debian、工具和依赖，不把浮动镜像标签当版本证据。

测试容器使用--rm --network none，不挂载设备、个人配置或Docker socket。服务端和工具测试完整执行；静态检查显式使用server/pyproject.toml，工作流配置检查实际运行。源码快照纳入当前已跟踪工作树内容，排除参考检出及运行目录；核对关键源码与当前文件一致。

另用同一官方Python基线的核心依赖镜像验证无开发/固件依赖的真实CLI启动、诊断、HTTP页面和状态；不安装ADB，检查明确缺少ADB行为。只监听容器loopback，不映射主机端口，结束回收子进程。

Linux3.10容器通过不证明Ubuntu远程runner或用户原生桌面通过；不证明手机控制或模型任务完成。每项记录实际退出码和限制；若环境依赖遗漏先修复环境，若产品实现失败先修正规格/范围再实施。
