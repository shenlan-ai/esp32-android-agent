# 验证记录

初始条件：已确认BLE0.1.2就绪、实际键鼠报告及停止释放；用户已手动切英文。实际结果与收尾见下文。

首次检查原生小米笔记停在用户协议页，未代为同意；用户自行完成后实际空笔记首页可见。准备离线备用工具，localhost GET / /notes /whiteboard /state均200；畸形事件400、32769B事件413，源码Ruff通过。

hello首次生产任务21.83s，4调用6301 tokens，0输入，因协议连续错误失败。只读诊断返回合法动作，没有执行；本机原配置私密备份后通过现有API设置JSON输出和temperature0，第二次任务继续实际验收。

hello第二次JSON配置：107.56s/17调用/31170tokens/6点击，坐标误判，0输入。独立guide-vlm-normalized-coordinates变更后第三次129.31s/22调用/41257tokens/5动作，恰好一次hello正文达成且标题为空，手机内容通过；结束阶段连续非法输出，生产任务failed，完整闭环未通过。不放宽校验或重放文字，保留原始export及截图。原生绘图入口已实际进入并由BLE产生笔划，继续完整目标核验。

原生笑脸第一次：210.55s/28调用/61838tokens/9动作，进入原生绘图页，2次swipe实际留下2段轮廓线；完整笑脸未完成，连续非法输出失败。离线备用白板首次86.59s/15调用/30563tokens/2动作，模型进入白板并真实绘制一笔，事件stroke_count=1、8个采样点，无完整笑脸。

协议只读诊断：简单上下文finish=stop/713completion tokens、合法JSON；完整任务上下文finish=length/1000completion tokens、content为空、reasoning_content3255字符，明确该次输出截断。实现前扩展proposal/design/tasks并strict通过，再用现有API把actor/planner的max_completion_tokens设为4096，保留JSON输出和temperature0及原总任务预算；供应商返回HTTP200、finish=stop、合法JSON（实际返回completion_tokens4265，以供应商实际usage记账）。未执行任何诊断建议。基于新截图启动继续已有笔划的任务，不清空或重放已有眼睛。

4096恢复最终382.12s / 17调用 / 91254tokens / 5次swipe；画板累计6笔、采样点8/13/17/16/18/26。独立goal_check拒绝不完整嘴部，后续笔划仍偏离且穿过已有左眼，因此主动停止，state=stopped；目标未完成，不标为通过。局部verified不能替代最终截图判断，仍保留模型几何判断与鼠标精度限制。

stop HTTP200、cancelled=true、hid_release_sent；最后mouse pointerup/buttons=0，未将其冒充中途停止时序证据。task/export/截图/事件均保存在ignored目录。已关闭8894/8895 fixture、移除reverse8894/8895及forward9224，仅8890继续监听；BLE hid_ready与calibrated均true，原生新建hello笔记/绘图草稿及用户设置保留，没有既有私人笔记修改或ADB替代输入。Android16/17、其他品牌、S3、旋转/拔线未执行。

最终归档前：`openspec validate --all --strict --no-interactive`19项通过；`openspec validate --archived --strict --no-interactive`26项通过；`.venv/Scripts/python.exe scripts/check_changes.py`138个修改文件范围通过；`git diff --check`退出0（仅Git CRLF提示）。工具HTTP/Ruff已通过，未增加或改动服务代码，不重复无变化的全回归；guide-vlm变更代码回归见其验证记录。验收任务完成指实际尝试、记录及收尾完成，不代表两个案例都通过。
