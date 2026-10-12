# screen-capture Specification

## Purpose
提供供用户预览和模型决策使用的有效安卓截图，并为每张图像保存明确的尺寸、编号与接收时间，使动作坐标不受显示留白影响，也不在设备或方向变化后误用旧画面。

## Requirements

### Requirement: Validated and bounded screenshot capture
系统 SHALL 校验截图完整性与尺寸，限制采集并发并复用短期预览缓存。失败 MUST 清除可操作画面状态，不把错误文本当图像。

#### Scenario: ADB returns truncated image data
- **WHEN** 采集数据不是完整有效图像
- **THEN** 画面接口失败并报告不可用，不执行依赖该画面的动作

### Requirement: Geometry changes invalidate old coordinates
系统 SHALL 使用 0–1000 坐标并映射至真实像素，校验坐标范围。设备与截图几何变化后 MUST 拒绝引用旧画面的动作。

#### Scenario: Rotation happens after preview
- **WHEN** 用户点击时当前截图尺寸与其引用的预览尺寸不同
- **THEN** 系统拒绝旧坐标并要求刷新画面

#### Scenario: Preview contains letterboxing
- **WHEN** 用户点击图像显示区域以外的留白
- **THEN** 网页不发送手机动作
