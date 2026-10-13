# 截图来源 / Image provenance

所有图片来自真实运行和手机截图，不使用生成图片、预置结果或假模型数据。原始图与私密运行记录保存在被忽略的本机目录，公开素材只保留测试内容。

| 文件 | 来源 | 处理 |
|---|---|---|
| `workbench.jpg` | 2026-10-13 本机 8890 生产工作台，BLE 控制，原生 hello 只读保存核验任务 completed | 默认浏览器视口的 872×3617 全页 JPEG，裁切顶部 872×840；以不透明色块遮盖 ADB 设备标识，标注 redacted；先用 UI 收起模型设置，未改变任务目标、结果或用量 |
| `real-phone-cases.png` 左侧 | 同日 Redmi Note14 5G / Android 15 / BLE 0.1.4，`strokes-014-smiley-result.png` 原始 1080×2400 | 裁切 x=0..1080、y=100..2050，去状态栏/浏览器底部工具栏，等比缩至 672×1213；保留本机白板标题和完整画线 |
| `real-phone-cases.png` 右侧 | 同日同设备，`acceptance-final-hello.png` 原始 1080×2400 | 裁切 x=0..1080、y=100..850，保留原生笔记工具栏、标题占位、时间和正文；等比缩至 672×467 |

案例图在截图外添加英文标签、背景和事实说明，合成为 1500×1580 PNG；未重画、修补或替换手机内容。裁切坐标以原始像素计；工作台页面未为美化截图改变视口。原始截图可能随本机清理而不可用，公开处理说明保留来源。

## 验收边界

白板为手机 Edge 内的本机测试页面，模型自行选择两次 circle 与一次 path，3 笔真实 HID 输入，独立最终目标核验通过；嘴为带棱角的折线。它不是原生绘图 App 的通过证明。

原生 hello 新建与输入达成，但创建任务自动结束失败，曾误选旧测试草稿并由人工清理/退出；之后单独只读模型任务核对新笔记保存通过。工作台展示的是这个保存核验任务，不能解读为单次全自动创建成功。完整条件与历史见[实机报告](../acceptance/2026-10-13-redmi-note14-ble.md)。

English: These are real production/device images. Only cropping, proportional resizing, identifier redaction and external captions were applied. The smiley used a browser test whiteboard. The native note required manual intervention between creation and a separate successful read-only check. Neither image proves universal compatibility or a task success rate.
