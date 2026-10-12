# BLE 串口协议 v1

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
