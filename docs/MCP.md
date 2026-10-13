# 用 MCP 接入 Codex 与其他 Agent

MCP 提供 `android_status`、`android_screenshot`、`android_action`、`android_stop` 四个工具。外部 Agent 使用工作台当前选择的手机与控制模式：ADB 获取画面，ESP32 BLE/USB 或 ADB 执行输入。桥接不重新打开串口，不要求安装手机 App，也不需要配置工作台的模型。

## 最短接入

先按 README 启动工作台，在网页选择手机、确认截图，选择控制模式；HID 坐标操作需先校准。源码目录执行：

```text
python -m pip install -e "./server[mcp]"
python -m android_agent --no-browser
```

工作台已运行时，只执行安装步骤。然后注册 stdio MCP。将下方 Python 路径替换为**安装了本项目 mcp extra 的 Python 绝对路径**（Windows 为 `.venv/Scripts/python.exe`，Linux/macOS 为 `.venv/bin/python`）：

```text
codex mcp add android_agent -- /absolute/path/to/python -m android_agent.mcp --url http://127.0.0.1:8890
codex mcp get android_agent
```

进入新的 Codex 会话后，要求它使用 `android_agent` MCP 读取状态和截图。Codex app 与 CLI 共用配置，已有聊天的工具目录不一定热加载；本功能已使用实际 Codex CLI 验收，见[验收记录](acceptance/2026-10-13-codex-mcp.md)。官方接入说明：[OpenAI Docs / MCP](https://developers.openai.com/codex/mcp)。

其他 MCP 客户端使用相同 stdio 命令：

```json
{
  "mcpServers": {
    "android_agent": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "android_agent.mcp", "--url", "http://127.0.0.1:8890"]
    }
  }
}
```

便携工作台也可以作为服务端，但当前 exe 不包含 stdio MCP 入口。为独立桥接安装 Python >=3.10，并从本仓库安装 `./server[mcp]`，使用上述命令连接便携工作台。核心安装 `./server` 不安装 MCP SDK。服务和桥接支持不同 Python 进程。

## 工具契约

| 工具 | 参数 | 结果 |
|---|---|---|
| `android_status` | `{}` | 实际设备在线状态、当前模式、能力、任务/维护状态、最近画面元数据；不返回序列号或模型配置 |
| `android_screenshot` | `{}` | JPEG 图片和 JSON 文本元数据，包含 `observation_id`、原始宽高、年龄；最长边1280，保持完整截图比例 |
| `android_action` | `{"observation_id":"…","action":{…}}` | 单次输入完成结果；需重新截图确认手机结果 |
| `android_stop` | `{}` | 取消内部任务、当前及排队输入，使旧观察失效，报告实际输入释放结果 |

截图结果包含真正的 MCP `ImageContent`，图片直接进入 Agent 的视觉上下文；JSON 文本包含坐标和引用。为兼容 Codex 图片交付，截图成功结果不同时重复填 `structuredContent`。其他结果及错误提供结构化数据。

正常调用顺序：**状态 → 截图 → 一个动作 → 新截图核验**。例如：

```json
{
  "observation_id": "从刚才截图结果取得，不能编造",
  "action": {"action": "tap", "x": 500, "y": 300}
}
```

动作格式与现有 Action 相同，包括 `tap`、`swipe`、`long_press`、`scroll`、`type`、`key`、导航和 `wait`；`path`/`circle` 仅在当前 HID 声明且校准有效时可用。使用 `android_status.capabilities`，不能假定 ADB 支持绘图或 HID 支持安卓主页键。`type.text` 仅可打印 ASCII，输入法仍由用户手动切换英文。MCP 不接受 `action.frame_id`；用 opaque `observation_id`。

坐标是完整截图的 **0..1000 严格整数**，包括顶部状态栏、底部系统区域及浏览器栏；不是缩小图片的像素。`x=1000` 对应原图最右像素，`y=1000` 对应最下像素。参数、路径预算、校准仍使用已有服务端校验。

凭据在服务内存中最多保存8帧、最长60秒，不受网页频繁预览逐出。动作执行前在共用控制锁内取新图，检查目标区域/全图、方向、尺寸及会话绑定。任何已提交输入（包括网页输入）、停止、手机选择、模式或校准变化会使旧观察失效。同一画面上的并发请求至多提交一个动作。过期或被拒绝后请重新观察，不盲目重放。

## 控制权、取消和鉴权

网页内部自动任务运行时 MCP 输入会被拒绝。先在工作台暂停任务并等待释放，再接管；恢复内部任务时重新观察。MCP 不提供设备切换、固件刷写、模型密钥或任务历史工具。

工作台访问令牌通过桥接环境变量 `ANDROID_AGENT_ACCESS_TOKEN` 传入，并使用现有 CSRF 保护。不要将令牌放 URL 或聊天中。Codex 可在本机私有配置传递 `env_vars = ["ANDROID_AGENT_ACCESS_TOKEN"]`；从设置了该变量的进程启动客户端。桥接只接受 `http://127.0.0.1`、`http://localhost`、`http://[::1]` 根地址，不使用 HTTP 环境代理、不跟随重定向。

控制动作会产生真实手机输入，工具如实标记写操作/可能有副作用，Codex 可能要求确认。非交互 `codex exec` 的 `approval_policy=never` 配合默认工具策略会拒绝此类输入。对于用户已经明确授权的测试，可仅在该次运行覆盖 `mcp_servers.android_agent.tools.android_action.approval_mode="approve"`；日常配置保留客户端审批策略。验收使用单次覆盖，没有修改用户全局配置。

控制 HTTP 超时/断开会返回 `transport_uncertain`，输入可能已经执行；桥接不重试，尽力在4秒内请求共享停止。MCP 客户端发送 `notifications/cancelled` 或关闭连接时，在途控制尽力停止释放；强制杀死进程无法保证清理，请使用 `android_stop`。Python SDK1.30.0仅取消本地 await 不会自动发送该通知，客户端需发送协议取消或显式调用 stop。错误使用 `isError=true` 和固定提示，不回显输入、令牌或上游错误正文。

`release` 表示真实控制器的释放报告，不保证物理设备已经处理；命令 `ok` 也不代表任务完成。截图失败、受保护/纯黑画面会作废观察并停止释放；恢复设备后重新观察。手机截图会进入所选外部 Agent 的模型上下文，应按自己的数据需求选择模型服务。

## 验证与排错

```text
python -m pip install -e "./server[dev,mcp]"
python -m pytest -q server/tests/test_mcp.py server/tests/test_mcp_api.py
python server/tests/mcp_demo.py --port 8900
```

将桥接 URL 改为 `http://127.0.0.1:8900` 可让实际 Codex 检查标有 DEMO 的假手机；该服务不打开真实 ADB/串口，不调用模型。实机准备可另运行 `python server/tests/mcp_demo.py --phone-page --port 8901`，用 ADB reverse 将同端口映射到手机，在手机浏览器打开本机页面。页面只记录测试输入，不提交到外部服务。完成测试后关闭自己启动的 fixture。

- `service_version`：更新并重启工作台；旧进程不包含 MCP HTTP 路由。
- `access_denied`：检查令牌、服务URL和本机配置。
- `device_rejected`：查看状态和工作台，检查在线手机、HID就绪、校准、内部任务及维护；重新截图。
- `stale_observation`：截图过期、已使用、画面或会话变化；重新截图后再决策。
- `screen_unavailable`：黑屏/受保护画面或采集断线，观察已失效且已请求停止；恢复手机后重新观察。
- `invalid_arguments`：检查嵌套 action、整数坐标、ASCII、动作必需字段与当前能力。
- `transport_uncertain`：恢复连接，重新截图确认结果，不重放未知输入。

该功能尚不提供远程MCP/OAuth、多手机控制或自动输入法切换。物理兼容性依现有[兼容表](COMPATIBILITY.md)，模拟和协议测试不能代替实机验收。
