## Decisions

- CI仅contents:read，不使用手机、串口、模型密钥或付费服务。Actions固定经官方仓库核验的commit；Python选3.10最低版本和3.12便携构建版本，Node22仅开发测试/OpenSpec。
- Python矩阵Ubuntu与Windows、3.10/3.12，执行Ruff和pytest；Node坐标独立于用户运行依赖。Windows跳过文件symlink实测，不把跳过当作成功；Linux应实际执行该测试。
- 独立治理job fetch-depth0，PR与base SHA比较，push与before SHA比较，首次push用empty tree，workflow_dispatch与HEAD比较。基准SHA来自环境并验证为Git revision，用参数调用，避免拼接用户输入shell。
- 四板Linux矩阵固定PlatformIO6.1.19，编译后esp32dev job执行全部工具测试，确保真实共享g++22场景不能因缺ArduinoJson而跳过。其他矩阵仅编译该板。
- 便携构建仅workflow_dispatch，在Windows3.12构建四板，然后运行构建脚本、Expand-Archive、smoke，再upload-artifact；只上传ZIP和SHA，不上传临时data/Flash备份、工作目录或平台缓存。失败不上传成功产物。
- 默认不开缓存以减少状态不一致；后续依据真实CI耗时另立优化变更。Ubuntu/Windows预装g++以命令检查；仅Linux固件job依赖原生编译器。
- 新增本地workflow结构检查，PyYAML6.0.3仅作为dev依赖，对固定Actions SHA、只读权限、矩阵、无设备命令和artifact范围做验收；如果actionlint可用则执行完整GitHub语法检查。配置的本地检查和等效本机命令不能替代首次远程运行。

## Validation

OpenSpec strict、范围检查、workflow结构检查及actionlint；本机同样Python/Ruff/Node/四板构建/工具测试/真实便携smoke证据。无Linux执行环境时明确待远程验收。不推送仓库、不上传发布。
