## Context

应用现为 FastAPI + 静态资源，用户数据已在独立目录。Windows 使用 PyInstaller one-folder，避免 one-file 每次解压开销和隐式临时路径。源代码模式继续跨平台。

## Decisions

1. 固定 PyInstaller 6.16.0，仅列入 build extra。发布构建记录实际 Python 和运行依赖版本，收集 dist-info 许可和 Python LICENSE。产物包含源码清单；排除 dev 依赖，禁止复制整个工作目录。
2. 启动先独占绑定 socket，再交给 uvicorn；只有 Server.started 后才打开本机页面。默认便携版自动打开，源码须 --open-browser；--no-browser 用于自动验证。远程模式不自动打开页面或将密钥放 URL。
3. ADB 优先 CLI，其次 ADB_PATH，然后便携根 platform-tools/adb.exe，最后 PATH。缺失仍启动工作台，诊断提供官方路径；不下载、运行未知工具或再分发未核定的 Platform Tools。
4. 固件打包清单 v1 包含 profile、family、chip_id、flash_bytes、bootloader/application offset、app 分区大小、镜像长度和 SHA256。经典使用4MB、bootloader0x1000；S3分别8/8/4MB、bootloader0。分区必须 OTA_0、app0x10000，镜像互不覆盖并在 Flash 内。
5. 对编译产物做芯片与分区验证后复制。来源记录 git revision、dirty 状态、固定 PlatformIO 配置。附本项目源码、Arduino core 2.0.17 和 ArduinoJson 7.4.2 官方源码归档及校验、LGPL 对象文件/链接信息，方便重新构建；不会将许可证归纳成全部 MIT。锁定官方仓库tag和真实commit，稀疏检出实际使用的源码目录生成tar并记录SHA256，不获取数百MB的预编译SDK；构建须核对commit和本机依赖版本，失败不输出成品。
6. 构建仅写忽略的 dist/build 目录或显式全新输出目录，不递归删除已有内容，不覆盖旧包。ZIP 用明确文件列表；使用解压后 exe 真正启动验证，测试不接触手机、串口、付费模型、真实用户配置。

## Risks and boundaries

Windows unsigned exe 可能触发 SmartScreen；当前不做代码签名。便携包构建成功不代表全机型兼容。正式发布前仍需要实机验收和依赖许可人工核查。刷写工具、网页固件向导、CI 自动构建另立变更。

## Validation

有意义的 launcher 测试覆盖 ADB优先级、端口冲突与远程 browser 条件；构建工具测试覆盖芯片错配、超分区、产物变动校验、路径越界；实际 one-folder 构建、ZIP 解压到含空格/中文路径、无Python依赖环境的真实 exe smoke，验证页面/资源/API和退出。完整现有检查做回归。
