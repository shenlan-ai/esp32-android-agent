from __future__ import annotations

import asyncio
import io
import json
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import __version__
from .adb import AdbClient
from .agent import RUNNING_STATES, TaskRunner
from .ble import (
    BleController,
    BridgeSelection,
    Calibration,
    PointerProbe,
    SerialBridge,
    serial_ports,
)
from .config import ConfigStore, PreferencesUpdate, RuntimeSettings
from .errors import AgentError
from .history import EventBus, TraceStore
from .llm import ModelClient, ModelProtocolError, parse_object
from .models import Action
from .screen import AdbScreen
from .session import DeviceSession

STATIC = Path(__file__).parent / "static"


def index_html() -> str:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for asset in ("app.js", "style.css"):
        html = html.replace(
            f'"/static/{asset}"', f'"/static/{asset}?v={(STATIC / asset).stat().st_mtime_ns}"'
        )
    return html


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    serial: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:\-]+$")


class Address(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address: str = Field(min_length=3, max_length=260)


class Pair(Address):
    code: str = Field(pattern=r"^\d{6}$")


class Goal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1, max_length=2000)


def create_app(settings: RuntimeSettings | None = None, adb=None, model_factory=ModelClient) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = settings or RuntimeSettings.from_env()
        runtime.check_access()
        app.state.settings = runtime
        app.state.csrf = secrets.token_urlsafe(32)
        app.state.store = ConfigStore(runtime.data_dir)
        app.state.preferences = app.state.store.load()
        client = adb or AdbClient(runtime.adb_path, runtime.command_timeout)
        app.state.adb = client
        app.state.session = DeviceSession(client, AdbScreen(client, runtime.preview_interval))
        # Remember the selection, but do not assume it is still online or authorized.
        if app.state.preferences.serial:
            try:
                await app.state.session.select(app.state.preferences.serial)
            except AgentError:
                pass
        app.state.events = EventBus()
        app.state.traces = TraceStore(runtime.data_dir)
        app.state.runner = TaskRunner(app.state.session, app.state.traces, app.state.events,
                                      model_factory, runtime.access_token.get_secret_value())
        app.state.model_probe = None
        try:
            yield
        finally:
            try:
                if app.state.model_probe and not app.state.model_probe.done():
                    app.state.model_probe.cancel()
                    await asyncio.gather(app.state.model_probe, return_exceptions=True)
                await app.state.runner.stop()
            finally:
                await app.state.session.close()

    app = FastAPI(title="ESP32 Android Agent", version=__version__, lifespan=lifespan)

    @app.middleware("http")
    async def access(request: Request, call_next):
        runtime = getattr(request.app.state, "settings", None)
        if runtime:
            if runtime.local_only and request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
                return JSONResponse({"detail": "Invalid local host"}, 403)
            origin = request.headers.get("origin")
            if origin and (
                urlparse(origin).netloc != request.headers.get("host")
                or urlparse(origin).scheme != request.url.scheme
            ):
                return JSONResponse({"detail": "Cross-origin requests are not allowed"}, 403)
            if request.url.path.startswith("/api/"):
                expected = runtime.access_token.get_secret_value()
                if expected and not secrets.compare_digest(
                    request.headers.get("x-agent-token", ""), expected
                ):
                    return JSONResponse({"detail": "Enter the configured access token"}, 401)
                if request.method not in {"GET", "HEAD", "OPTIONS"}:
                    if not secrets.compare_digest(
                        request.headers.get("x-agent-csrf", ""), request.app.state.csrf
                    ):
                        return JSONResponse(
                            {"detail": "Refresh the page before sending controls"}, 403
                        )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path == "/" or request.url.path.startswith(("/static/", "/api/")):
            response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; connect-src 'self'"
        )
        return response

    @app.exception_handler(AgentError)
    async def agent_error(_, exc):
        return JSONResponse({"detail": str(exc)}, 409)

    @app.exception_handler(RequestValidationError)
    async def request_error(_, exc):
        return JSONResponse(
            {
                "detail": [
                    {"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()
                ]
            },
            422,
        )

    @app.exception_handler(ValidationError)
    async def settings_error(_, exc):
        return JSONResponse({"detail": "Invalid settings; check URL, limits and extra fields"}, 422)

    @app.exception_handler(ValueError)
    async def value_error(_, exc):
        return JSONResponse({"detail": str(exc)}, 422)

    @app.get("/")
    async def index():
        return HTMLResponse(index_html())

    @app.get("/api/session")
    async def browser_session():
        return {"csrf": app.state.csrf, "version": __version__}

    @app.get("/api/status")
    async def status():
        session = app.state.session
        calibrated = False
        if isinstance(session.controller, BleController) and session.controller.calibration:
            calibration = session.controller.calibration
            frame = session.screen.frame
            calibrated = bool(
                frame
                and (calibration.phone, calibration.width, calibration.height)
                == (frame.serial, frame.width, frame.height)
            )
        return {
            "version": __version__,
            "adb_available": app.state.adb.available,
            "serial": session.serial,
            "mode": session.controller.mode if session.controller else None,
            "capabilities": session.controller.capabilities if session.controller else [],
            "frame": session.screen.frame.public() if session.screen.frame else None,
            "agent": app.state.runner.public(include_steps=False),
            "board": session.controller.bridge.public()
            if isinstance(session.controller, BleController)
            else None,
            "calibrated": calibrated,
        }

    @app.get("/api/boards")
    async def boards():
        return {"ports": serial_ports()}

    @app.post("/api/control/mode")
    async def control_mode(selection: BridgeSelection):
        session = app.state.session
        bridge = None
        if selection.mode == "ble":
            if not selection.port or selection.port not in {p["port"] for p in serial_ports()}:
                raise ValueError("Choose a connected ESP USB/UART serial port")
            bridge = SerialBridge(selection.port)
        calibration = app.state.preferences.ble_calibrations.get(session.serial)
        await session.set_mode(selection.mode, bridge, calibration)
        return {"ok": True, "mode": selection.mode}

    @app.post("/api/control/calibrate")
    async def calibrate(calibration: Calibration):
        await app.state.session.calibrate(calibration)
        app.state.preferences.ble_calibrations[calibration.phone] = calibration
        app.state.store.save(app.state.preferences)
        return {"ok": True}

    @app.post("/api/control/locate")
    async def locate(probe: PointerProbe):
        return await app.state.session.locate(probe)

    @app.get("/api/devices")
    async def devices():
        return {"devices": [d.model_dump() for d in await app.state.adb.devices()]}

    @app.post("/api/devices/select")
    async def select(selection: Selection):
        await app.state.session.select(selection.serial)
        app.state.preferences.serial = selection.serial
        app.state.store.save(app.state.preferences)
        return {"ok": True, "serial": selection.serial}

    @app.post("/api/adb/pair")
    async def pair(payload: Pair):
        await app.state.adb.pair(payload.address, payload.code)
        return {"ok": True}

    @app.post("/api/adb/connect")
    async def connect(payload: Address):
        await app.state.adb.connect(payload.address)
        return {"ok": True}

    @app.get("/api/adb/discover")
    async def discover():
        return {"services": await app.state.adb.discover()}

    @app.get("/api/frame.png")
    async def frame():
        captured = await app.state.session.screen.capture()
        return Response(
            captured.png,
            media_type="image/png",
            headers={
                "Cache-Control": "no-store",
                "X-Frame-Id": str(captured.id),
                "X-Frame-Width": str(captured.width),
                "X-Frame-Height": str(captured.height),
            },
        )

    @app.post("/api/action")
    async def action(payload: Action):
        return await app.state.session.execute(payload)

    @app.post("/api/stop")
    async def stop():
        if app.state.model_probe and not app.state.model_probe.done():
            app.state.model_probe.cancel()
            await asyncio.gather(app.state.model_probe, return_exceptions=True)
        return {"ok": True, **await app.state.runner.stop()}

    @app.get("/api/task")
    async def task_snapshot():
        return app.state.runner.public()

    @app.post("/api/task/start")
    async def start_task(payload: Goal):
        if app.state.model_probe and not app.state.model_probe.done():
            raise AgentError("Wait for the model test to finish before starting a task")
        return await app.state.runner.start(payload.goal, app.state.preferences)

    @app.post("/api/task/pause")
    async def pause_task():
        return await app.state.runner.pause()

    @app.post("/api/task/resume")
    async def resume_task():
        return await app.state.runner.resume(app.state.preferences)

    @app.post("/api/task/clear")
    async def clear_task():
        return await app.state.runner.clear()

    @app.get("/api/task/steps/{index}/{phase}.jpg")
    async def step_image(index: int, phase: str):
        if phase not in {"before", "after"}:
            raise ValueError("Choose before or after step image")
        data = app.state.runner.images.get((index, phase))
        if data is None:
            raise AgentError("Step image expired or unavailable; check exported history if saved")
        return Response(data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/api/history")
    async def task_history():
        return {"tasks": await app.state.traces.list()}

    @app.get("/api/history/{task_id}")
    async def history_snapshot(task_id: str):
        return await app.state.traces.read(task_id)

    @app.get("/api/history/{task_id}/export.zip")
    async def export_history(task_id: str):
        data = await app.state.traces.export(task_id)
        return Response(data, media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="task-{task_id}.zip"',
                                 "Cache-Control": "no-store"})

    @app.get("/api/events")
    async def events(request: Request):
        if len(app.state.events.queues) >= 32:
            raise AgentError("Too many event subscribers; close unused browser tabs")

        async def stream():
            async with app.state.events.subscribe() as queue:
                yield 'event: reset\ndata: {}\n\n'
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15)
                        yield f"event: {event['event']}\ndata: {json.dumps(event)}\n\n"
                    except TimeoutError:
                        yield ': heartbeat\n\n'
        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/models/test")
    async def test_model():
        if app.state.runner.state in RUNNING_STATES:
            raise AgentError("Pause or finish the task before testing a model")
        if app.state.model_probe and not app.state.model_probe.done():
            raise AgentError("A model test is already running")

        async def probe():
            stream = io.BytesIO()
            Image.new("RGB", (64, 64), "#008000").save(stream, "JPEG")
            client = model_factory(app.state.preferences.actor)
            try:
                reply = await client.chat('Return only JSON {"color":"dominant color in English"}.',
                                          "What is the dominant color of this synthetic square?", [stream.getvalue()])
                result = parse_object(reply.text)
                if str(result.get("color", "")).lower() != "green":
                    raise ModelProtocolError("Endpoint responded but did not identify the synthetic image")
                return {"ok": True, "seconds": round(reply.seconds, 3),
                        "tokens": reply.usage.total_tokens, "estimated": reply.usage.estimated,
                        "phone_image_sent": False}
            finally:
                await client.close()
        pending = asyncio.create_task(probe(), name="model-connectivity-probe")
        app.state.model_probe = pending
        try:
            return await pending
        except asyncio.CancelledError as exc:
            raise AgentError("Model test cancelled; no phone input was sent") from exc
        finally:
            if app.state.model_probe is pending:
                app.state.model_probe = None

    @app.get("/api/settings")
    async def get_settings():
        return app.state.preferences.public()

    @app.post("/api/settings")
    async def save_settings(update: PreferencesUpdate):
        app.state.preferences = app.state.store.update(app.state.preferences, update)
        return app.state.preferences.public()

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
