"""MCP acceptance fixture: offline simulated phone or a local no-submission phone page."""
from __future__ import annotations

import argparse
import io
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from conftest import FakeAdb
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from PIL import Image, ImageDraw

import android_agent.app as app_module
from android_agent.config import RuntimeSettings

PHONE_PAGE = """<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MCP LOCAL TEST</title><style>
body{background:#eef5fa;color:#173b55;font:22px sans-serif;padding:20px;margin:0}
h1{font-size:26px} button,input{font:24px sans-serif;box-sizing:border-box;width:100%;padding:20px;margin:16px 0;border:2px solid #00756c;border-radius:8px}
button{background:#00756c;color:white;min-height:100px} #result{min-height:70px;font-weight:bold}
</style><h1>MCP LOCAL TEST</h1><p>NO SUBMISSION / NO EXTERNAL SERVICE</p>
<button id="tap">MCP TAP TEST</button><p id="result">Waiting for a tap</p>
<label for="text">ASCII input test</label><input id="text" placeholder="Type mcp_hello here" autocomplete="off">
<p id="typed">Input: (empty)</p><p id="release">Pointer events recorded locally.</p>
<script>
let taps=0; const out=document.getElementById('result'), txt=document.getElementById('text');
function record(value){fetch('/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)}).catch(()=>{})}
document.getElementById('tap').onclick=()=>{out.textContent='MCP TAP OK — '+(++taps);record({kind:'tap',taps})};
txt.oninput=()=>{document.getElementById('typed').textContent='Input: '+txt.value;record({kind:'input',value:txt.value})};
txt.onfocus=()=>{document.getElementById('release').textContent='FOCUS OK - ASCII input active';record({kind:'focus'})};
txt.onblur=()=>{document.getElementById('release').textContent='Input not focused';record({kind:'blur'})};
for(const kind of ['pointerdown','pointerup','pointercancel'])document.addEventListener(kind,e=>record({kind,x:Math.round(e.clientX),y:Math.round(e.clientY),buttons:e.buttons}));
</script></html>"""


class McpDemoPhone(FakeAdb):
    def __init__(self):
        super().__init__()
        self.tapped, self.text = False, ""

    async def run(self, *args, **kwargs):
        image = Image.new("RGB", (400, 800), "#eef5fa")
        draw = ImageDraw.Draw(image)
        draw.text((20, 20), "DEMO - SIMULATED PHONE", fill="#173b55", font_size=22)
        draw.rectangle((30, 160, 370, 320), fill="#00756c")
        draw.text((65, 225), "MCP TAP OK" if self.tapped else "MCP TAP TEST", fill="white", font_size=28)
        draw.text((30, 400), "Input: " + (self.text or "(empty)"), fill="#173b55", font_size=24)
        draw.text((20, 730), "NO REAL HARDWARE", fill="#173b55", font_size=22)
        output = io.BytesIO()
        image.save(output, "PNG")
        self.png = output.getvalue()
        return await super().run(*args, **kwargs)

    async def shell(self, serial, *args):
        if "tap" in args and 30 <= int(args[-2]) <= 370 and 160 <= int(args[-1]) <= 320:
            self.tapped = True
        if args[:2] == ("input", "text"):
            self.text += args[-1].replace("%s", " ")
        return await super().shell(serial, *args)


def create_demo():
    app_module.serial_ports = lambda: []
    directory = tempfile.TemporaryDirectory(prefix="android-agent-mcp-demo-")
    app = app_module.create_app(RuntimeSettings(data_dir=Path(directory.name)), McpDemoPhone())
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        try:
            async with original(app):
                await app.state.session.select("phone1")
                yield
        finally:
            directory.cleanup()
    app.router.lifespan_context = lifespan
    return app


def create_phone_page():
    app = FastAPI()
    recorded = []

    @app.get("/")
    async def index():
        return HTMLResponse(PHONE_PAGE, headers={"Cache-Control": "no-store"})

    @app.post("/events")
    async def event(request: Request):
        value = await request.json()
        recorded.append(value)
        del recorded[:-1024]
        return {"ok": True}

    @app.get("/events")
    async def events():
        return {"events": recorded}

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8900)
    parser.add_argument("--phone-page", action="store_true")
    args = parser.parse_args()
    uvicorn.run(create_phone_page() if args.phone_page else create_demo(), host="127.0.0.1", port=args.port)
