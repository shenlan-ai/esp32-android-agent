## Context

当前四板产物已校验，经典COM5已在授权后刷入0.1.0并通过通信测试，手机输入仍待验收。网页默认本机并使用CSRF/可选访问令牌。固件安装是用户发起的设备维护操作，模型动作集合不包含刷写。

## Decisions

1. 公用stdlib board_info与firmware_catalog承载现有芯片解析和镜像布局验证；CLI沿用同一验证。catalog只接受已支持profile，JSON限长、拒绝重复key；实际芯片头、分区、offset、长度和SHA必须与manifest严格一致，不信任manifest提供的任意路径。
2. 独立工具tools/firmware_worker.py使用esptool5.3.0的Python API，仅提供identify/backup/write/diagnose。应用调用参数列表子进程，不导入GPL esptool。工具单独GPL-2.0-or-later许可与完整对应源码随包提供；应用MIT边界保持在进程/协议接口。固定上游v5.3.0的真实commit，记录实际工具依赖和校验。
3. 工具每次连接ROM后读取芯片、MAC和Flash；backup/write校验预期身份并在同一连接内执行，物理掉线失败，不按COM端口重新连接并重放写入。identify不加载stub或写Flash；backup/write仅在需要时加载RAM stub。写入与verify_flash使用内存中已验证的镜像字节和相同DIO/40MHz/容量参数，避免文件改动与bootloader头更新造成误判。
4. 经典仅4MB、S3分别8/8/4MB匹配。芯片不能证实商品板型，S3 8MB的两个profile让用户显式选择；未支持Flash容量/系列拒绝备份写入流程。备份是全Flash，校验完整长度、SHA和原子完成状态，非完成的part文件不能用于写入或下载。
5. manager维护单一job和后台task；session维护操作标志同步占用，拒绝活跃/暂停任务、输入、模式切换、选择手机、校准、配网/监听竞争；不在整个固件IO期间占用session action lock，使手机紧急停止仍可即时完成且不触碰固件子进程。所有进入设备控制的方法前后检查维护标志，过期请求不在刷写结束后执行。
6. identify完成后释放维护标志。用户选择profile才开始备份；备份成功后生成300秒一次性确认ticket，绑定job、设备身份、profile、备份SHA和镜像SHA。前端显示目标、备份、覆盖说明和默认未选的确认框。write请求StrictBool true及正确ticket后消耗ticket，重探身份，检查备份/暂存manifest/镜像，再写与读取验证。失败保留备份，报告未知/未验证结果，不重放。
7. 每个job UUID对应私有目录的镜像快照，0600文件；读写不得使用用户提供路径。备份记录在独立user data/firmware-backups，以job ID查找，下载使用授权fetch+blob，不把访问令牌放URL。原Flash可能含敏感配置，提示保存在本机且不要公开上传。历史元数据不保存确认ticket；服务重启不自动恢复或写入。
8. HTTP端点返回任务状态后由GET轮询；后台操作不会因HTTP取消而丢失。只允许取消识别/备份；写入与校验期间取消请求拒绝。服务优雅关闭等待拥有的固件操作结束；强制终止进程或断电无法由软件保证，失败恢复以完整备份和显式重新识别为入口。
9. subprocess并发读取stdout/stderr，stdout仅结构化结果，stderr有界保留且不对网页回显原始内容；超时/取消终止该工具树并回收句柄。写入超时结果未知；不自动重试。源码需要可选firmware extra，缺工具/镜像网页说明安装；便携根自动定位tool/firmware，不增加Node或Arduino用户依赖。

## UI plan and review

复用现有调试工作台，不重做主界面。颜色沿用背景#f1f5f8、白纸#ffffff、正文#183b56、辅助#5b6b79、操作#006e68、覆盖提示#b52b37；Segoe UI/微软雅黑承担现有层级。全部左对齐，窄屏换行，保留focus和减少动画设置。编号只标实际连续步骤：

```text
识别串口  [识别开发板]  → 芯片 / 容量 / 商品板型未确认
选择固件  [只列匹配profile]
完整备份  [备份当前程序] → 容量 / SHA / 下载
确认覆盖  [未选确认框] [写入并校验]
```

特征来自真实硬件安装流程；不增加营销hero、通用卡片或额外装饰。状态区显示实际阶段与耗时，不编造整体百分比。写入时说明关闭网页不会停止、手机Esc不会中断Flash。双语按钮与结果使用同一命名。

## Validation and boundaries

关键测试：真实catalog的四板校验、身份替换、stub前拒绝、短备份、checksum/manifest篡改、未确认/错误/重用/过期ticket、串口互斥、HTTP取消、写入取消拒绝、优雅关闭、超时进程树清理、worker同一连接及实际读写字节/verify参数。使用fake ROM调用真实独立worker代码，不接物理板。另有带DEMO标识的离线浏览器完整流程，真实打包工具diagnose和页面烟测。可在已授权当前板上只读识别；本轮不会再次写COM5。S3/手机实物和真实模型验收不能由模拟替代。
