import asyncio

import httpx
from test_agent import DONE, PLAN, VERIFIED, ScriptedModels

from android_agent.app import create_app
from android_agent.config import RuntimeSettings


async def test_task_api_records_images_export_clear_and_model_probe(tmp_path, fake_adb):
    models = ScriptedModels([{"color": "green"}, PLAN, DONE, VERIFIED])
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb, models)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://localhost"
    ) as client:
        client.headers["X-Agent-CSRF"] = (await client.get("/api/session")).json()["csrf"]
        assert (await client.get("/api/status")).json()["agent"]["available"]
        assert (await client.post("/api/task/start", json={"goal": "Open Settings"})).status_code == 409
        await client.post("/api/settings", json={"actor": {"model": "test", "api_key": "private-key"}})
        probe = await client.post("/api/models/test", json={})
        assert probe.json()["ok"] and not probe.json()["phone_image_sent"] and fake_adb.screenshots == 0
        await client.post("/api/devices/select", json={"serial": "phone1"})
        started = await client.post("/api/task/start", json={"goal": "Open Settings"})
        assert started.status_code == 200 and started.json()["state"] == "planning"
        await asyncio.wait_for(asyncio.shield(app.state.runner._task), 3)
        snapshot = (await client.get("/api/task")).json()
        assert snapshot["state"] == "completed" and "private-key" not in str(snapshot)
        assert "steps" not in (await client.get("/api/status")).json()["agent"]
        image = await client.get("/api/task/steps/1/after.jpg")
        assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"
        assert (await client.get("/api/task/steps/1/invalid.jpg")).status_code == 422
        assert (await client.get("/api/task/steps/999/after.jpg")).status_code == 409
        history = (await client.get("/api/history")).json()["tasks"]
        assert history[0]["id"] == snapshot["id"]
        export = await client.get(f"/api/history/{snapshot['id']}/export.zip")
        assert export.status_code == 200 and export.content.startswith(b"PK")
        assert (await client.get("/api/history/not-a-task/export.zip")).status_code == 409
        await client.post("/api/task/clear", json={})
        assert (await client.get("/api/task")).json()["state"] == "idle"
        assert (await client.get("/api/history")).json()["tasks"]


async def test_sse_reset_changes_and_subscription_cleanup(tmp_path, fake_adb):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    class Request:
        async def is_disconnected(self):
            return False
    async with app.router.lifespan_context(app):
        endpoint = next(route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/events")
        response = await endpoint(Request())
        iterator = response.body_iterator
        assert "event: reset" in await anext(iterator)
        app.state.events.publish()
        assert "event: changed" in await anext(iterator)
        await iterator.aclose()
        assert not app.state.events.queues


async def test_stop_cancels_single_model_probe_and_closes_client(tmp_path, fake_adb):
    started, cancelled = asyncio.Event(), asyncio.Event()
    async def blocked():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    models = ScriptedModels([blocked])
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb, models)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://localhost"
    ) as client:
        client.headers["X-Agent-CSRF"] = (await client.get("/api/session")).json()["csrf"]
        await client.post("/api/settings", json={"actor": {"model": "test"}})
        first = asyncio.create_task(client.post("/api/models/test", json={}))
        await started.wait()
        assert (await client.post("/api/models/test", json={})).status_code == 409
        assert (await client.post("/api/task/start", json={"goal": "x"})).status_code == 409
        assert (await client.post("/api/stop", json={})).status_code == 200
        assert (await first).status_code == 409
        assert cancelled.is_set() and models.closed == 1 and app.state.model_probe is None
