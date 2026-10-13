"""Offline browser acceptance fixture; never accesses ADB, serial or external models."""
import asyncio
import io
import json
from pathlib import Path

import httpx
import uvicorn
from conftest import FakeAdb
from fastapi.responses import HTMLResponse, RedirectResponse
from PIL import Image, ImageDraw

import android_agent.app as app_module
from android_agent.config import ConfigStore, ModelSettings, Preferences, RuntimeSettings
from android_agent.llm import ModelClient


class DemoPhone(FakeAdb):
    def __init__(self):
        super().__init__()
        self.page = "home"
        self.entries[0].model = "DEMO simulated Android"

    async def run(self, *args, **kwargs):
        image = Image.new("RGB", (360, 720), "#ecf1f5")
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 20, 344, 90), fill="#173b55")
        draw.text((30, 42), "SIMULATED ANDROID", fill="white")
        draw.text((30, 120), "Wi-Fi settings" if self.page == "wifi" else "Home screen", fill="#173b55")
        draw.rounded_rectangle((25, 190, 335, 300), 12, fill="#00756c")
        draw.text((45, 235), "Wi-Fi: ON" if self.page == "wifi" else "Open Wi-Fi settings", fill="white")
        draw.text((30, 590), "OFFLINE DEMO - NO REAL PHONE", fill="#173b55")
        output = io.BytesIO()
        image.save(output, "PNG")
        self.png = output.getvalue()
        return await super().run(*args, **kwargs)

    async def shell(self, serial, *args):
        await super().shell(serial, *args)
        if "tap" in args:
            self.page = "wifi"
        if "keyevent" in args and "3" in args:
            self.page = "home"
        return b""


def create_demo():
    # Fixture routes must reject every physical board port, even on a host with COM5 attached.
    app_module.serial_ports = lambda: []
    phone = DemoPhone()
    delay = 0.4
    async def provider(request):
        await asyncio.sleep(delay)
        body = json.loads(request.content)
        system = body["messages"][0]["content"]
        if system.startswith("Plan"):
            value = {"plan": "1. 打开 Wi-Fi 设置\n2. 核验 Wi-Fi 开关"}
        elif system.startswith("Choose"):
            value = ({"action": "tap", "x": 500, "y": 340,
                      "reason": "画面中显示 Wi-Fi 设置入口，点击它。", "expected": "Wi-Fi 设置页和开关可见。"}
                     if phone.page == "home" else {"action": "done", "reason": "已看到 Wi-Fi 设置页。", "answer": "已打开 Wi-Fi 设置，模拟开关为开启。"})
        elif system.startswith("Independently"):
            value = {"confirmed": phone.page == "wifi", "evidence": "模拟画面显示 Wi-Fi settings 与 Wi-Fi: ON。"}
        else:
            value = {"color": "green"}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(value, ensure_ascii=False)}}],
                                         "usage": {"total_tokens": 120}})

    directory = Path(".runtime-local/agent-demo")
    prefs = Preferences(serial="phone1", actor=ModelSettings(base_url="https://demo.invalid/v1", model="DEMO visual model"), save_screenshots=True)
    ConfigStore(directory).save(prefs)
    app = app_module.create_app(RuntimeSettings(data_dir=directory), phone,
                                lambda settings: ModelClient(settings, httpx.MockTransport(provider)))
    app.router.routes[:] = [route for route in app.router.routes if getattr(route, "path", None) != "/"]

    @app.get("/")
    async def index():
        banner = '<section class="access"><strong>DEMO 离线模拟：不连接真实手机、开发板或模型服务</strong><a href="/demo/reset">重置模拟手机</a><a href="/demo/slow">慢请求模式</a><a href="/demo/fast">正常速度</a></section>'
        return HTMLResponse(app_module.index_html().replace(
            '<main id="console-main">', banner + '<main id="console-main">'
        ))

    @app.get("/demo/reset")
    async def reset():
        await app.state.runner.stop()
        phone.page = "home"
        return RedirectResponse("/")

    @app.get("/demo/slow")
    async def slow():
        nonlocal delay
        delay = 5
        return await reset()

    @app.get("/demo/fast")
    async def fast():
        nonlocal delay
        delay = 0.4
        return await reset()

    return app


if __name__ == "__main__":
    uvicorn.run(create_demo(), host="127.0.0.1", port=8892)
