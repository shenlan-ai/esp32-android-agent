"""Explicit offline firmware DEMO: no real serial, ADB, or model operations."""
import argparse
import asyncio
import tempfile
from pathlib import Path

import uvicorn
from conftest import FakeAdb
from fastapi.responses import HTMLResponse
from test_firmware import FakeTool, fakes

from android_agent import app as app_module
from android_agent.config import RuntimeSettings
from android_agent.errors import DeviceError
from android_agent.firmware import FirmwareManager


class DemoTool(FakeTool):
    async def run(self, operation, *args, timeout=30):
        await asyncio.sleep(1)
        if "DEMO-OFFLINE" in args:
            raise DeviceError("DEMO: simulated disconnected board. Select DEMO-ESP32 and identify again.")
        return await super().run(operation, *args, timeout=timeout)


def create_demo(folder):
    tool = DemoTool()
    settings = RuntimeSettings(data_dir=folder / "data", firmware_dir=fakes.make_catalog(folder / "catalog"))
    app_module.serial_ports = lambda: [
        {"port": "DEMO-ESP32", "description": "DEMO memory-backed ESP32; no physical device"},
        {"port": "DEMO-OFFLINE", "description": "DEMO simulated disconnect"}]

    def no_model(*args, **kwargs):
        raise DeviceError("DEMO: real model use disabled")

    app = app_module.create_app(settings, FakeAdb(), model_factory=no_model,
                               firmware_factory=lambda runtime, session, idle:
                               FirmwareManager(runtime, session, idle, tool=tool))
    for route in app.routes:
        if getattr(route, "path", None) == "/":
            async def demo_index():
                return HTMLResponse(app_module.index_html().replace("<body>",
                    '<body><p class="firmware-error">DEMO · Offline simulation · 无实物设备、真实 ADB 或模型调用</p>'))
            route.endpoint = demo_index
            route.dependant.call = demo_index
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8892)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="firmware-demo-") as temporary:
        uvicorn.run(create_demo(Path(temporary)), host="127.0.0.1", port=args.port)
