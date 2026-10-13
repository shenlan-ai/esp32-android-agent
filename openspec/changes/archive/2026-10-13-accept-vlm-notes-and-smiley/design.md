## Decisions
使用已有TaskRunner，一次一个动作、截图独立核验、能力约束及未知输入先观察。准备时ADB只负责启动App/测试页面，不能用ADB注入动作冒充BLE。仅修改新建测试笔记；遇到隐私/联网授权不代为同意，记录暂停/未完成。

现有分段swipe允许角形笑脸，不能声称连续曲线。离线备用页仅canvas接受实际pointer事件画线；textarea只接受真实键盘，首页入口由模型点击，工具本机监听且主动启动、无外部资源/设备控制、记录有界事件与实际结果。

## Validation
模型生产task状态/步骤/用量，真实手机截图及可能的DOM事件交叉检查。工具HTTP与Ruff，OpenSpec strict、范围检查。完成或失败都如实记录；不以模型自称完成代替目标验收。

## 模型格式恢复
首次原生hello任务21.83秒/4调用/6301 tokens，0动作，因三次协议错误失败。只读同画面诊断返回合法tap(837,846)，finish=stop，未执行。为兼容可支持的OpenAI格式供应商，使用现有extra_body配置response_format=json_object和temperature=0，保留原配置本机备份；若供应商拒绝则恢复。此项只改变用户本机模型配置，不放宽JSON/动作校验或执行诊断建议。重新启动目标前确认画面及0动作，避免重放未知输入。

后续只读诊断：简单上下文合法，但完整任务/近期步骤上下文耗尽1000token，finish_reason=length、content为空，reasoning_content存在。通过现有设置API对actor/planner设置max_completion_tokens=4096（已有校验上限），保留其余extra_body与总任务预算。先只读探测供应商支持，再根据新图开启有界任务继续已有笔划；不清空、重画已有输入或放宽严格输出解析。此诊断只证明该次截断原因，不能解释所有历史协议失败。
