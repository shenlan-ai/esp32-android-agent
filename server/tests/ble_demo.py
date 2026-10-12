"""Local browser acceptance fixture. Never opens serial or invokes real ADB."""

from __future__ import annotations

from pathlib import Path

import uvicorn
from conftest import FakeAdb
from fastapi.responses import HTMLResponse, RedirectResponse
from PIL import Image, ImageDraw

from android_agent import app as app_module
from android_agent.ble import CAPABILITIES
from android_agent.config import RuntimeSettings


class DemoBridge:
    paired = False

    def __init__(self, port):
        self.port = port
        self.connected = False
        self.capabilities = sorted(CAPABILITIES)

    @property
    def ble_connected(self):
        return self.paired

    async def open(self):
        self.connected = True

    async def close(self):
        self.connected = False

    async def stop(self):
        return {"cancelled": True, "release": "demo_no_physical_input"}

    async def request(self, *args, **kwargs):
        return {"status": "done", "elapsed_ms": 20, "button_held_ms": 0}

    def public(self):
        return {
            "port": self.port,
            "connected": self.connected,
            "ble_connected": self.paired,
            "firmware": "DEMO",
            "ble_name": "SIMULATED",
            "error": None,
        }


def create_demo():
    app_module.SerialBridge = DemoBridge
    app_module.serial_ports = lambda: [
        {"port": "SIMULATED", "description": "DEMO: no real hardware", "vid": 0x10C4, "pid": 0xEA60}
    ]
    adb = FakeAdb()
    adb.entries[0].model = "DEMO simulated phone"
    image = Image.new("RGB", (200, 400), "#eef7f7")
    ImageDraw.Draw(image).text((30, 160), "SIMULATED PHONE", fill="#175f66")
    import io

    output = io.BytesIO()
    image.save(output, "PNG")
    adb.png = output.getvalue()
    app = app_module.create_app(RuntimeSettings(data_dir=Path(".runtime-local/ble-demo")), adb)
    app.router.routes[:] = [
        route for route in app.router.routes if getattr(route, "path", None) != "/"
    ]

    @app.get("/")
    async def index():
        html = app_module.index_html()
        banner = '<section class="access"><strong>DEMO 模拟验收：不会操作真实手机或开发板</strong> <a href="/demo/pair">模拟蓝牙配对</a> <a href="/demo/reset">模拟取消配对</a></section>'
        return HTMLResponse(html.replace("<main>", banner + "<main>"))

    @app.get("/demo/pair")
    async def pair():
        DemoBridge.paired = True
        return RedirectResponse("/")

    @app.get("/demo/reset")
    async def reset():
        DemoBridge.paired = False
        return RedirectResponse("/")

    return app


if __name__ == "__main__":
    uvicorn.run(create_demo(), host="127.0.0.1", port=8891)
