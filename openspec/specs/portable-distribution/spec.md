# portable-distribution Specification

## Purpose
让 Windows 用户通过可核验的解压包启动本机工作台，同时将运行依赖、固件来源和真实验证范围清楚记录，降低安装成本并避免携带开发者的个人数据。

## Requirements

### Requirement: Self-contained local application
Windows便携应用 SHALL 包含Python运行时和网页，默认仅监听本机，数据保存在包外用户目录。启动器 MUST 在自己的服务成功启动后才自动打开浏览器，端口占用时明确失败。

#### Scenario: Start in an extracted path
- **WHEN** 用户在含空格或中文的目录解压并启动便携包
- **THEN** 页面与静态资源可用，不要求系统安装Python、Node或Arduino，数据不写入程序资源目录

#### Scenario: Port belongs to another program
- **WHEN** 启动器绑定的端口已被使用
- **THEN** 启动失败并说明更换端口，不打开或接管已有服务

### Requirement: Explicit external ADB selection
启动器 SHALL 支持显式ADB路径、环境变量、便携根platform-tools目录和PATH，依次选择。缺失ADB SHALL 允许网页启动并提供诊断，文档 MUST 链接官方来源且不得宣称已经随包提供ADB。

#### Scenario: ADB is missing
- **WHEN** 用户未提供或安装ADB
- **THEN** 工作台可加载，ADB诊断不可用，用户能按官方Platform Tools说明补充工具

#### Scenario: An explicit ADB overrides adjacent tools
- **WHEN** 用户指定 --adb 且包旁也存在platform-tools
- **THEN** 使用用户指定路径

### Requirement: Verifiable distribution contents
便携构建 MUST 记录实际依赖版本、许可、项目版本、源码来源和SHA256，不复制个人配置、密钥、原始Flash备份或参考检出。四板固件 SHALL 包含明确的Flash布局和镜像校验，错误芯片、分区或超容量产物 MUST 被拒绝；对应源码和重新构建信息 SHALL 随包提供。

#### Scenario: Wrong firmware image
- **WHEN** S3 profile 对应镜像头标记经典ESP32或应用超出声明分区
- **THEN** 构建拒绝该产物，不生成成功发布清单

#### Scenario: Inspect the package
- **WHEN** 用户查看发布包
- **THEN** 可核对各镜像和依赖来源及许可，项目个人数据与参考检出不在包内

### Requirement: Real extracted-process validation
便携包验收 MUST 使用解压后可执行程序的真实子进程，覆盖页面、静态资源、API、缺ADB和端口冲突。模拟验收 SHALL 不执行真实输入或将结果描述为手机兼容。

#### Scenario: Run smoke without devices
- **WHEN** 验证脚本启动便携程序
- **THEN** 使用隔离数据目录和缺失ADB路径，验证 HTTP 行为与进程退出，不接触用户设备或配置
