# 安全与隐私 / Security and privacy

本项目当前为开发阶段，未建立稳定版本的安全支持周期。维护者按可复现报告处理问题，不能承诺固定响应时间。

## 数据与运行边界

- 默认网页只监听本机 `127.0.0.1`。主动开放远程访问时配置访问令牌并使用可信网络，不直接暴露到公网。S3 的认证 TCP 通道没有传输加密。
- 模型密钥、设备配置、Wi-Fi 凭据与任务数据默认位于用户目录 `.esp32-android-agent`，可用 `--data-dir` 更改。不要提交或分享整个数据目录。
- 自动任务将手机截图发送到你配置的视觉模型服务。模型连通性测试仅使用合成图。请先检查屏幕内容和服务的数据政策；“服务本机运行”不等于模型请求离线。
- 截图存盘默认关闭；开启后截图进入本机任务记录和导出。已知密钥/令牌被脱敏，但目标、模型文字和屏幕本身仍可能包含私人信息。分享前自行审查导出与截图。
- 完整 Flash 备份可能含原程序的密钥或网络配置。保留备份用于恢复，不公开上传。固件写入需要明确确认；不要拔线或强制终止写入。
- ADB 调试与 BLE/USB HID 是手机实际控制通道。只连接自己授权的设备，测试时使用空白内容，完成后按需撤销调试授权或断开配对。

## 报告问题

普通缺陷可提交[Issue](https://github.com/shenlan-ai/esp32-android-agent/issues)，只附脱敏复现。涉及密钥泄漏、未授权控制或绕过访问限制的漏洞，请使用仓库 Security 页的 **Report a vulnerability** 私密入口（若已启用）。若入口不可用，先通过不含漏洞细节的 Issue 请求私密联系方式，再私下提供细节。不要在公开 Issue/PR 上传凭据、原始 Flash、私人手机截图或完整任务导出。

报告应包括代码提交/版本、主机系统、脱敏设备/固件信息、最小复现、预期和实际结果。泄漏凭据应先撤销并轮换；删除工作树文件不能清除 Git 历史或已公开副本。

## English

The project is in development with no stable-version security support schedule. The web service binds to localhost by default. S3 TCP authentication is not encryption. Automatic tasks send phone screenshots to your configured model endpoint; the connection test uses a synthetic image.

Keep the user data directory, keys, Wi-Fi configuration, raw task exports and full flash backups private. Screenshot saving is off by default. Redaction of known credentials cannot remove private information visible in goals or screens.

For a vulnerability, use **Report a vulnerability** on the repository's Security page when available. Otherwise request a private contact through an issue containing no exploit details or sensitive data. Include the affected revision and a minimal redacted reproduction. Rotate exposed credentials; removing a file does not remove its Git history.
