# 验证记录

实现前：hello第二次JSON模式任务107.56s/17调用/31170 tokens/6点击，5次核验失败、1次切回笔记页通过，目标未完成。无文字输入。

实现后：Python3.12.14与3.10.21全服务端测试各239通过、1 Windows symlink权限skip、1依赖弃用warning；全源码Ruff通过，工具57测试及Node5测试通过。画像测试覆盖竖屏、横屏、小图、尺寸不变、原bytes不变及非网格内容可见；闭环测试验证actor使用网格而planner和核验保持干净。已检查真实手机网格预览。

生产服务重启后BLE0.1.2仍hid_ready=true，当前竖屏校准可用。真实hello第三次成功切笔记、点击新建、一次输入hello，干净截图确认正文只有hello且标题为空；随后结束阶段非法输出使生产任务失败。坐标尺在这次导航中有效，但单次结果不能证明模型通用精度或完整任务稳定性。没有重复输入或放宽协议。

白板真实复验也使用网格：原生与备用页均产生真实笔划，但完整笑脸未完成。提高既有输出额度至4096后，备用白板恢复5次swipe/382.12s/17调用/91254tokens；独立核验拒绝错误done，笔划偏离后主动停止。网格不能消除几何误判、局部核验误判及鼠标轨迹偏差，未作通用精度声明。手机输入已释放，测试fixture/映射已清理；具体证据由accept-vlm-notes-and-smiley及脱敏报告保留。

最终归档前：`openspec validate --all --strict --no-interactive`19项通过；`openspec validate --archived --strict --no-interactive`26项通过；`.venv/Scripts/python.exe scripts/check_changes.py`138个修改文件范围通过；`git diff --check`退出0（仅Git CRLF提示）。上述完整回归后无代码变化，仅补实机结果与文档，未重复全回归；其他手机、Android16/17、S3及旋转/拔线实测未执行。
