## 1. Preparation
- [x] 1.1 严格校验更新后的变更，重新截取真实新版控制台且手机画面是常规状态。
## 2. Alarm recording
- [x] 2.1 通过 Codex 的 android_agent MCP 设置一个新的未来闹钟并逐步截图核验，不修改或删除现有闹钟。
- [x] 2.2 录制、拉取并验证闹钟 MP4，调用 android_stop 释放输入。
- [x] 2.3 保留初次误导航及ADB模式通用device_rejected的失败记录，停止录屏并确认释放；不以ADB注入替代MCP。
## 3. README and media
- [x] 3.1 移除 README 首屏手机效果图，加入更新控制台截图及常规手机画面说明。
- [x] 3.2 在英文和中文 README 内嵌两个视频并保留回退链接；补齐 MCP 支持与使用方式、闹钟复现提示和边界。
- [x] 3.3 写验收记录、媒体来源和验证结果。
- [x] 3.5 上传两个授权演示MP4取得实际GitHub附件URL，核验GitHub播放器而非仅HTML标签。
- [x] 3.4 替换 README 里的手机笑脸静态图，用更新后的普通手机画面控制台截图；笑脸视频改为内嵌播放器及下载回退。
## 4. Completion
- [x] 4.1 完成 OpenSpec、Markdown、媒体、范围和差异检查后归档变更，再复核正式/归档规格。
