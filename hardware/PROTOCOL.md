# HID 桥协议 v1

BLE0.1.4 / USB0.1.2新增`path`能力。仅握手声明该能力时主机才列path/circle；旧固件和ADB不提供。线上只发送path：`{"action":"path","points":[[100,200],[300,250],[200,400]],"duration_ms":500}`（仍需v/session/id/op）。points为2–20个严格整数计数对，范围0–4000；每段ceil(max(abs(dx),abs(dy))/8)之和最多500报告，全部参数验证后才accepted。重复和闭合点允许，额外字段、非法类型/结构、越界或超预算拒绝。

路径归位/定位首点后按下一次，连续通过所有段后释放一次；段间不归位、不松开。各段沿用共同整数插值，BLE50ms/USB10ms，每次调度至多一运动报告；duration_ms为整笔最低按压时长50–5000ms。停止/断线/心跳失效立即清除剩余段，不重放。最大允许路径仍在BLE60秒/USB30秒主机期限内。

模型path的点仍为完整画面0–1000，主机逐点映射为计数后复核预算；circle由中心x/y及x轴半径r展开为按完整画面比例校正的16边闭合路径(17点)，越出画面即拒绝、不裁剪。两动作继承校准版本门禁与陈旧画面校验。连续能力和报告预算测试不代表手机绘画或VLM成功；当前经典板已刷入0.1.4、读取校验及BLE键鼠就绪通过，Redmi Note14 / Android15竖屏重新校准531/1176计数，闭合多段path/circle及第二段中途停止释放实测通过。VLM成功、其他机型与USB实物需另行验收。

BLE 0.1.3 / USB 0.1.1 的定位和拖动使用共同线段进度：N=ceil(max(abs(dx),abs(dy))/8)，第i个报告发送带符号round(abs(axis)*i/N)与上一累计位置之差。每轴报告不超过8，累计线误差不超过0.5个HID计数，最终总位移精确；零向量不发送运动报告，定位切换到拖动时重置进度。报告保持两轴比例，不再先耗尽短轴后补长轴。BLE50ms/600ms等待、USB10ms、按压最低时长及可取消调度不变。升级必须重新校准；此保证针对报告计数，安卓鼠标加速和手机像素精度需另行实测。

## 经典 ESP32 BLE 串口

传输为115200 UART，UTF-8 JSON行，最大1024字节。固件会忽略超长行直到换行，主机拒绝发送超长消息。启动时ROM串口日志不是JSON，主机忽略。协议不是任意命令执行接口。

握手：`{"v":1,"id":1,"op":"hello","session":""}`。响应status=hello，包括32位会话字符串、chip=esp32、firmware、ble_name、ble_connected、capabilities。新的hello释放输入并使旧会话失效。

之后每条消息携带v、session、id、op。动作id为会话内单调递增整数；重复最近已接受的动作id仅返回running或保存结果，较旧编号被拒绝。仅一个动作在执行，其他动作返回busy。主机每个动作只发一次，不自动重试。

| op | 参数 | 结果 |
|---|---|---|
| heartbeat | id=0 | heartbeat；主机500ms发送一次，固件1500ms超时释放 |
| status | 无 | ready及ble_connected |
| stop | 无 | 当前动作cancelled，然后stopped；释放状态与手机是否仍连接分开 |
| action | action及参数 | accepted，然后done/error/cancelled；accepted不代表输入或目标完成 |

动作：tap(x,y)、long_press(x,y,duration_ms)、swipe(x,y,x2,y2,duration_ms)、scroll(x,y,lines)、type(text)、key(key)、wait(duration_ms)。校准专用locate(x,y)只移动不点击；底层move(dx,dy)只作调试。所有位置以校准相对计数表示，范围0–4000；move范围±4000；ASCII最多512字符；持续50–5000ms，长按最少400ms，滚轮±1–10。

每次坐标动作先用50个(-127,-127)、10ms间隔报告归位。经典BLE固件0.1.1在归位后通过调度器等待600ms，再用最大步幅8、50ms间隔移动；等待不阻塞主循环，也不按下按钮。它用于减少BLE分组传输与归位后的速度历史影响，实际落点仍需手机校准验收。原生USB保持最大步幅8、10ms间隔及零归位等待。滑动沿用各自校准时的相同节奏，duration_ms表示按下的最低时长：移动提前结束则在终点保持后释放，移动所需时间更长则以实际移动为准。done包含elapsed_ms（含归位）及button_held_ms（不含归位）；主机返回execution字段供查看，不将其视为精确触摸时序或手机目标成功。BLE坐标和locate的主机响应等待上限60秒，键盘/USB维持30秒，超时不重发。结束释放键鼠。ASCII按美国键盘映射，手机若使用其他布局需手动确认实际输出。

主机校准保存实际握手firmware；0.1.0历史无版本记录仅用于0.1.0，更新到0.1.1后必须重新校准，不能将旧节奏计数直接用于新固件。BLE和USB的firmware必须为1–64字符ASCII字符串，首字符为字母或数字，其余允许字母、数字、点、下划线、加号和连字符；大小写无关的unknown占位无效。缺失、结构值、空白、非法或超长字段保持未知，不转换或截断。未知或失配版本不列坐标能力，未知版本拒绝保存校准并保留已有配置；键盘不依赖坐标校准，原始locate可用于无按钮诊断。

BLE断线时板子清理本地输入状态、停止动作并使会话失效；不能声称已经断开的手机收到了释放报告。主机断开依赖板上心跳看门狗；主机确认失败应显示释放未确认。重新连接始终重新hello，不重放旧动作。

ble_connected表示已完成加密配对，且键盘和鼠标报告已订阅。报告GATT提交失败或订阅失效时不报告done，会使会话失效。stopped附带release_sent；该字段只表示释放报告成功提交到BLE栈，不证明手机目标或上层应用状态。主机仅在该字段为true时报告hid_release_sent。

经典BLE固件0.1.2在所有有效串口回复（含hello）增加可选`ble_state`：`link`、`authenticated`、`keyboard_subscribed`、`mouse_subscribed`为布尔，`auth_error`为null或0–255整数。链路由GATT回调记录，订阅来自真实CCCD；最近认证失败保留原因码，认证成功或断线清除错误，断线清除链路和认证。无MAC、密钥或原始认证日志。异步快照只用于提示，不能代替`ble_connected`或启用输入，也不主动设订阅。

主机只保存完整且严格类型正确的五个字段，忽略额外字段；旧固件缺失、非法快照或串口断线均公开未知。USB不使用BLE诊断。0.1.2保持0.1.1鼠标节奏，但校准仍绑定真实版本，升级需重新校准。

此物理串口通道没有LAN令牌。蓝牙使用加密绑定配对，手机必须主动选定设备。不是抗恶意近场配对或高安全遥控产品。

## ESP32-S3 USB / TCP

使用相同 JSON v1 会话和动作，TCP最大行长1024字节，枚举状态字段为`usb_connected`，hello的chip为`esp32s3`，另含12位小写MAC格式`board_id`和`profile`。枚举只表示USB主机接入，不识别手机；键盘/鼠标report ID为1/2。

TCP先认证再hello：主机发`{"v":1,"op":"challenge","nonce":"<64hex>"}`，板子回`{"v":1,"op":"authenticate","board_id":"<12hex>","proof":"<64hex>"}`。证明为`HMAC-SHA256(64字符ASCII密钥, "android-agent-usb-v1:" + nonce + ":" + board_id)`。挑战每连接随机更新，主机常量时间比较。最多8个待认证连接，认证响应3秒超时、hello3秒超时；另一认证握手进行中或已有活跃板子时拒绝替换。首版每服务配对一块板子，首次配网才启用默认8891监听。

去重、时序和500ms/1500ms心跳与BLE一致。网络输出单次非阻塞send，部分写入或失败关闭连接；USB报告有界等待20ms，失败不报告done，重试中性释放并拒绝新动作直至释放完成。断网、重新配网、USB失效和看门狗使会话失效。TCP关闭不证明手机收到释放，状态区分已发送/未确认。重连创建新会话，主机要求显式重绑，不恢复旧动作。

CDC只用于配置：`{"v":1,"id":1,"op":"get_config"}`读取身份，返回status=config、chip、board_id、protocol=`android-agent-usb-v1`、firmware、profile和configured。`configure`接受ssid、password、host(IPv4)、port、token(64hex)，保存NVS单条JSON后回status=configured并重建Wi-Fi。身份不符在写入前拒绝，非法配置status=error。响应无密码/密钥，CDC不接受action；物理配置接口由设备持有人使用。

TCP没有TLS，仅用于可信局域网，不接收手机截图或模型密钥。板子端口独立于本机网页，网页保留CSRF/令牌保护。详见[USB说明](../docs/USB-SETUP.md)。
