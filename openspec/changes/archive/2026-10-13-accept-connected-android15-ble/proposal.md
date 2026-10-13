## Why

用户已连接并授权Redmi Note14 5G Android15/API35，并明确确认Android Agent BLE配对及要求尝试操作。当前固件HID就绪；首版仍缺真实手机输入、校准与释放证据。现有模拟无法证明落点和输入只发生一次，需要无账号/无外部提交的本机测试页面记录实际浏览器事件。

## What Changes

- 增加仅本机、主动启动的输入验收fixture；页面提供空文本字段、不同位置目标、可拖动/滚动区域和有界事件记录，不控制手机或调用模型。用现有ADB reverse和手机浏览器访问，ADB仅负责测试准备，BLE动作经过生产工作台API。
- 在同一手机与COM5上实测画面、HID校准、点按/长按/滑动/滚动、ASCII键盘和紧急停止；采集可观察页面事件和截图，未通过不标为通过。
- 记录脱敏的具体型号/Android/API、固件、运行代码、控制路线、动作耗时/落点/释放与限制；更新兼容文档，保留Android16/17、S3与真实模型待验收。发现产品问题先另立规格再修复，不回改旧归档。

## Capabilities

### Modified Capabilities
- continuous-validation: 增加显式启动的真实输入测试页面，软件CI保持无设备。

## Impact

新scripts/phone_input_fixture.py与docs/acceptance/2026-10-13-redmi-note14-ble.md，兼容与BLE/验收入口文档。临时记录/私人截图/地址均在忽略目录，不提交配置、地址或凭据。不刷固件、不安装伴侣App、不要求Root，不发送/提交外部表单，不启动未配置的付费模型。
