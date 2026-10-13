## Decisions
detect_chip仍115200，完成同一连接ROM初始化、身份核对和run_stub后，backup不调用change_baud。write仍调用460800，绝不在失败后重新连接或再次写入。容量期限max(600, flash_bytes / 8192 + 60)，覆盖4MB和8MB，仍有界。真实当前4MB低速备份要完整通过下载长度与SHA256；局部64KB成功不证明4MB成功，其他板型未实测。

## Validation
向导worker按256KB连续范围调用esptool官方read_flash，保留其每段传输摘要检查。逐段检查bytes类型与实际长度，再合成有界4MB/8MB内容；任何中间失败不得落盘为完成备份，不重试、不重连，不自行修改esptool协议或超时。测试验证实际范围连续无重叠、末段、后续段错误终止、完整SHA及单次连接。CLI低速参数统一但仍为一次读取，不将局部诊断当作整片证据。

传统scripts/flash_board.py显式向run传递backup的115200/600秒，write保留默认460800/180秒。实际子进程参数测试核验完整4MB内容和SHA；读取失败不生成完成散列且main不启动write。

假ROM跟踪实际baud并在高速read_flash注入传输失败，验证生产backup完整内容/散列/一次连接且不提高速率，write速率保持。主机测试覆盖8MB期限。两Python版本回归、Ruff、实际COM5完整备份与下载核验，OpenSpec范围检查。
