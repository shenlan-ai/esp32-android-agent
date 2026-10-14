# Design

## 现状与边界

内置 Agent parse_decision 和 MCP ObservedAction 均使用 Action；12种输入已可执行。MCP4工具足够承载截图、状态、单步动作、停止，无需为每种动作增加另一个执行入口。内置 done/fail/replan 为编排状态，不向设备发送输入。BLE/USB不支持Android导航键，ADB不支持持续path/circle；必须遵守实际控制器能力。

## 方案

将既有 ACTION_EXAMPLES 移至 models（Agent继续导入同一名称）。MCP状态提供 allowed_keys、action_examples、action_rules，仅包含当前能力；读取能力一次，未连接/维护/无就绪时返回空清单。所有结果保持脱敏、不含设备标识或设置。MCP schema说明整数完整截图坐标、每种动作参数、持续笔画2..20点、圆形r为横向归一化半径且保持真实像素圆形、ASCII和按键规则。继续由原Action与控制器校验，不裁剪或降级。

以真实SDK list_tools/call_tool验证声明、样例解析、各ADB动作命令与HID连续笔画实际转换，重复/非法/停止/画面失效沿用现有保护。增加动作集合与共享模型/示例相等断言，未来新增动作必须同步。

真实Codex工具发现把Pydantic tuple的prefixItems显示为字符串数组；对MCP公开schema将每个点表达为标准items整数数组（minItems=maxItems=2），外层仍2..20点，坐标0..1000。运行时保留原StrictInt tuple校验，不接收字符串或浮点。SDK测试同时验证JSON Schema对合法/非法点的结果，并以新客户端检查整数声明，不能靠文字描述掩盖错误类型。

本机项目.codex/config.toml指向本仓库.venv Python源码MCP，忽略该文件并保留其他用户配置。仅为本次已授权笔记绘图临时设android_action审批策略，结束后恢复原策略；无密钥或全局设置修改。新桌面会话用原生MCP调用，禁止shell/ADB替代输入，只新建笔记、绘图、保存，不编辑/删除其他笔记。每步截图→动作→新截图；不重放未知输入，最终重新打开核验保存和释放。实机阻塞如锁屏/断线由用户恢复，记录真正成功或失败，不能用模拟证明实机成功。

## 验证与兼容

无需固件编译或便携包重建。真实结果仅对当前Redmi Note14/Android15/经典ESP32 BLE0.1.4有效，不证明所有应用/手机。原始截图与会话输出在.runtime-local，提交记录不含私人笔记。测试通过后按OpenSpec归档，实机未完成则保持活动状态并记录限制。
