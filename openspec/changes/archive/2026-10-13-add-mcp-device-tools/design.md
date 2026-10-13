# Design

采用官方 Python MCP SDK 1.30.0（可选 mcp extra；dev同时安装用于CI），低层Server + stdio；保持网页核心依赖独立。CLI `android-agent-mcp --url http://127.0.0.1:8890` / `python -m android_agent.mcp`。仅支持本机服务；远程访问/OAuth不在范围。

四工具：status 返回筛选状态及当前能力；screenshot 返回JPEG ImageContent、原始尺寸和opaque observation_id；action接收observation_id及嵌套严格Action（frame_id不由客户端指定）；stop复用/api/stop。SDK初始化instructions指示单步观察→动作→观察，0..1000、ASCII、能力门禁及结果未知不重放。业务失败用isError和固定提示，协议保留结构化结果。

专用HTTP端点错误提供白名单code：stale_observation、screen_unavailable、device_unavailable，桥接仅映射固定文案，不转发上游detail。这样Agent可明确区分需刷新截图与连接/控制冲突，不泄漏设备错误或输入。

新增/api/mcp/status、/screenshot、/action，由现有访问中间件鉴权/CSRF保护。ObservationStore生命周期属于app，保存最多8个Frame，60秒有效，不依赖预览history；存会话epoch及input_revision。捕获在共用会话锁中，停止可取消。所有现有输入提交前增revision；校准增epoch。MCP动作锁内检查binding，重新取图并复用validate_decision（tap局部，其他全图），on_submit原子消耗观察。停止、选择、模式和校准变化均使凭据失效。错误参数不会消耗未提交凭据，真正提交/不确定执行必然失效。

桥接使用httpx有限超时、trust_env=False、follow_redirects=False、受控路径；每次写先获取CSRF，不重试任何HTTP写入。一次工具操作包含CSRF在内总期限30秒，另有最多4秒释放清理。错误响应不回显上游文本/令牌/输入。action超时、取消或断开尽力独立有限停止；停止不等待action锁。截图失败或黑屏清空观察并停止；不以命令ok代替手机结果验证。正常stdio客户端关闭若有在途控制由取消路径释放，不无故停止其他客户端的闲置会话。

截图成功结果仅提供TextContent元数据及ImageContent，不重复填structuredContent：Codex CLI0.154.0首轮实测同时返回structuredContent时，协议日志有image但Agent只读到元数据。非图片结果保留structuredContent。SDK测试检查两块内容，真实Codex再次检查图片可见性，不以协议有图片等同模型看见。

文档给源码和独立桥接/便携工作台配置，Codex命令使用绝对Python路径；不修改用户全局Codex配置，验收用单次CLI覆盖配置。测试用假ADB/控制器、真实SDK ClientSession和真实stdio子进程；Codex先在DEMO验收，实机只控制无提交的本机测试页，保留脱敏证据，不刷固件。若实机断线明确报告并保持必要验收任务未完成。

手机测试页另记录focus并显示FOCUS OK标记，要求外部Agent看到真实焦点后才输入；保留首次定位失败与空输入证据，不将错误坐标改写为通信成功。定位修正后作为独立验收轮次记录。
