## ADDED Requirements
### Requirement: Identity evidence for installation
安装识别 SHALL 记录芯片系列、硬件MAC和真实Flash容量，MAC缺失或不受支持容量不得生成写入准备；商品PCB继续标记未确认。共享CLI解析 SHALL 保留旧识别语义。

#### Scenario: S3 8MB has multiple profiles
- **WHEN** 识别到S3与8MB Flash
- **THEN** 列出匹配8MB的已支持profile供用户选择，不将芯片结果当作确定XIAO或DevKitC商品板型
