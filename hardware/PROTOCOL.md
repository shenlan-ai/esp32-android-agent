# HID 桥协议 v1

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

每次坐标动作先用50个(-127,-127)报告归位，再用最大步幅8、10ms间隔移动。滑动沿用相同节奏，duration_ms表示按下的最低时长：移动提前结束则在终点保持后释放，移动所需时间更长则以实际移动为准。done包含elapsed_ms（含归位）及button_held_ms（不含归位）；主机返回execution字段供查看，不将其视为精确触摸时序或手机目标成功。结束释放键鼠。ASCII按美国键盘映射，手机若使用其他布局需手动确认实际输出。

BLE断线时板子清理本地输入状态、停止动作并使会话失效；不能声称已经断开的手机收到了释放报告。主机断开依赖板上心跳看门狗；主机确认失败应显示释放未确认。重新连接始终重新hello，不重放旧动作。

ble_connected表示已完成加密配对，且键盘和鼠标报告已订阅。报告GATT提交失败或订阅失效时不报告done，会使会话失效。stopped附带release_sent；该字段只表示释放报告成功提交到BLE栈，不证明手机目标或上层应用状态。主机仅在该字段为true时报告hid_release_sent。

此物理串口通道没有LAN令牌。蓝牙使用加密绑定配对，手机必须主动选定设备。不是抗恶意近场配对或高安全遥控产品。

## ESP32-S3 USB / TCP

使用相同 JSON v1 会话和动作，TCP最大行长1024字节，枚举状态字段为`usb_connected`，hello的chip为`esp32s3`，另含12位小写MAC格式`board_id`和`profile`。枚举只表示USB主机接入，不识别手机；键盘/鼠标report ID为1/2。

TCP先认证再hello：主机发`{"v":1,"op":"challenge","nonce":"<64hex>"}`，板子回`{"v":1,"op":"authenticate","board_id":"<12hex>","proof":"<64hex>"}`。证明为`HMAC-SHA256(64字符ASCII密钥, "android-agent-usb-v1:" + nonce + ":" + board_id)`。挑战每连接随机更新，主机常量时间比较。最多8个待认证连接，认证响应3秒超时、hello3秒超时；另一认证握手进行中或已有活跃板子时拒绝替换。首版每服务配对一块板子，首次配网才启用默认8891监听。

去重、时序和500ms/1500ms心跳与BLE一致。网络输出单次非阻塞send，部分写入或失败关闭连接；USB报告有界等待20ms，失败不报告done，重试中性释放并拒绝新动作直至释放完成。断网、重新配网、USB失效和看门狗使会话失效。TCP关闭不证明手机收到释放，状态区分已发送/未确认。重连创建新会话，主机要求显式重绑，不恢复旧动作。

CDC只用于配置：`{"v":1,"id":1,"op":"get_config"}`读取身份，返回status=config、chip、board_id、protocol=`android-agent-usb-v1`、firmware、profile和configured。`configure`接受ssid、password、host(IPv4)、port、token(64hex)，保存NVS单条JSON后回status=configured并重建Wi-Fi。身份不符在写入前拒绝，非法配置status=error。响应无密码/密钥，CDC不接受action；物理配置接口由设备持有人使用。

TCP没有TLS，仅用于可信局域网，不接收手机截图或模型密钥。板子端口独立于本机网页，网页保留CSRF/令牌保护。详见[USB说明](../docs/USB-SETUP.md)。
