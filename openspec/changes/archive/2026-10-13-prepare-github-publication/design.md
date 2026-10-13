## Decisions
借鉴上游README的首屏演示、Why对比、Eyes/Hands/Brain、Quick start、Hardware及许可结构，内容基于安卓实现和实际证据。优势以安装路径、控制路线、网页向导及闭环保护为事实，不宣称全机型、任意App、性能优于竞品或无需安卓授权。

截图优先当前生产工作台真实完成任务与既有笑脸/原生hello手机截图；工作台截图裁切或遮盖本机设备序列号/接口等配置区域，保留任务结果/时间/动作证据。案例图可并列排版并加非UI标签，来源与处理写docs/images/README.md；截图不做内容替换或模型生成。若生产UI无法截图，采用已有真实证据及明示离线DEMO截图，不伪造生产画面。

正式文档展示当前状态，将旧版本结果明确标历史；原生hello创建任务曾失败且经人工纠错后独立保存核验通过，保持这一限制。Python最低3.10；普通安装只用server核心extra，可选固件维护独立说明；Windows便携说明区分本地开发产物与GitHub未发布二进制。

.gitignore扩大本地设置、任务导出、Flash备份、编译/IDE缓存范围但不忽略合法源码、图片、示例配置和规格。通过git check-ignore证明边界，不默认忽略所有JSON、ZIP或PNG掩盖必要交付文件。

提交前读取git staged/unstaged与当前历史；现有改动为本项目历次已归档工作，本次一并提交最终工作树，不使用旧暂存活动变更残片。按明确项目文件/目录git add -A，排除参考/个人数据。配置origin为用户指定GitHub仓库，无force push；先在私有仓库push并验证提交，再根据已获明确授权改公开。若远端非空先获取/检查，不覆盖无关历史。不创建Release、发通知给第三方或改用户其他仓库。
## Validation
公开页面发现 About 为空；按发布展示范围用 gh repo edit 添加事实性一句话描述和 android/esp32/vision-agent 等主题，不设置外部网站或更改其他仓库权限。
首次远端 CI 完成后，将 CONTRIBUTING/DEVELOPMENT 里的“首次远端未运行”更新为有 run/commit 证据的实际状态，保留旧模拟/容器记录。准备变更在首次 push 时活动目录已入 Git；files.txt 显式覆盖自身旧目录，以便最终归档的删除与新归档证据一同通过相对首次提交的范围检查。
检查中英事实一致、本地链接/图片存在与渲染、截图视觉质量/敏感区域、ignore正反样例、所有暂存文件及历史秘密/大文件；执行适用完整源码回归、Ruff、工具/Node/四板构建、OpenSpec全部/归档校验和范围检查。用户原始提交权限与目标仓库保持一致；远端main SHA==本地HEAD、visibility=PUBLIC、README与图片实际GitHub可读，工作树/剩余范围状态记录。
