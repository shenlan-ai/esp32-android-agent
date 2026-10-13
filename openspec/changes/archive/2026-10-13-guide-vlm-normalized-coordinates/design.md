## Decisions
在既有缩小JPEG上绘制细蓝线与边缘0/100/.../1000标签，大小不变、无额外边框，网格与完整截图百分比空间对应。动作模型才接收网格图，其余模型与导出图片仍使用干净JPEG/PNG。函数新建图像不改Frame原始bytes，在线程执行有限绘制避免阻塞loop。上下文提供width/height及coordinate_space，ACT_PROMPT说明网格用于坐标读取、不是手机UI。

## Validation
测试归一化边界、输出尺寸、原始bytes不变、真实模型调用actor带网格而planner干净；既有旧图/旋转/能力测试保持。3.10/3.12相关与完整回归、Ruff、实机重新观察后的hello及白板尝试、OpenSpecstrict/范围。实际效果仅限定当前模型和手机，不保证全机型精度。
