"""Offline USB setup fixture: fake CDC, loopback board, fake wireless ADB, no model IO."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from agent_demo import DemoPhone
from fastapi.responses import HTMLResponse
from test_usb import BOARD, FakeUsbBoard

import android_agent.app as app_module
from android_agent.config import ConfigStore, Preferences, RuntimeSettings


def create_demo():
    app_module.serial_ports = lambda: [{"port": "DEMO-S3", "description": "SIMULATED S3 CDC"}]
    app_module.provision_board = lambda *args: BOARD  # Never open a physical serial port.
    directory = Path(".runtime-local/usb-demo")
    ConfigStore(directory).save(Preferences(serial="phone1"))
    phone = DemoPhone()
    phone.entries[0].transport = "wireless"
    app = app_module.create_app(RuntimeSettings(data_dir=directory, usb_host="127.0.0.1", usb_port=8893), phone)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        async with original(app):
            boards = []

            async def monitor():
                while True:
                    usb = app.state.usb
                    if usb.server and not (usb.current and usb.current.connected):
                        board = FakeUsbBoard()
                        boards.append(board)
                        await board.connect(usb, key=usb._key)
                    await asyncio.sleep(0.2)

            task = asyncio.create_task(monitor())
            try:
                yield
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                for board in boards:
                    await board.close()

    app.router.lifespan_context = lifespan
    app.router.routes[:] = [route for route in app.router.routes if getattr(route, "path", None) != "/"]

    @app.get("/")
    async def index():
        banner = '<section class="access"><strong>DEMO S3 配网模拟：没有实物板子、手机或模型调用</strong></section>'
        return HTMLResponse(app_module.index_html().replace("<main>", banner + "<main>"))

    return app


if __name__ == "__main__":
    uvicorn.run(create_demo(), host="127.0.0.1", port=8892)
