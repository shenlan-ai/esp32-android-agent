# Validation

- 独立安装：`uv pip install --python .venv/Scripts/python.exe -e "./server[dev]"` 成功，Python 3.12.14。
- `pytest -q server/tests`：基础 36 项通过；停止释放期间拒绝新动作的回归场景加入后见最终命令结果。
- `ruff check server`、`ruff format --check server`：通过。
- `node --test server/tests/geometry.test.mjs`：3 项通过，覆盖横竖图留白与无图拒绝。
- 真实浏览器访问本机服务：无 ADB 时服务可启动并给出诊断；中英切换、无线表单展开正常，浏览器无 JS 错误。
- 响应式检查：移动宽度下文档 contentWidth = clientWidth = 375，无横向溢出。
- 配置与 API 集成测试覆盖密钥保留/清除、非法文本、跨站拒绝、截图尺寸和点按像素。
- 未进行真实手机、无线 ADB 或 ESP32 验收；模拟 ADB 测试不代表机型兼容性。
- 依赖 Starlette 提示未来 TestClient 推荐 httpx2；当前 httpx 接口测试通过，不影响产品运行。
