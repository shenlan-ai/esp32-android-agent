import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from android_agent.app import create_app
from android_agent.ble import BleController
from android_agent.config import RuntimeSettings


@pytest.fixture
def client(tmp_path, fake_adb):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    with TestClient(app, base_url="http://localhost") as client:
        client.headers["X-Agent-CSRF"] = client.get("/api/session").json()["csrf"]
        yield client


def test_manual_flow_needs_no_model(client, fake_adb):
    assert client.get("/").status_code == 200
    assert client.get("/api/devices").json()["devices"][0]["serial"] == "phone1"
    assert client.post("/api/devices/select", json={"serial": "phone1"}).status_code == 200
    response = client.get("/api/frame.png")
    assert response.headers["content-type"] == "image/png"
    result = client.post(
        "/api/action",
        json={
            "action": "tap",
            "x": 1000,
            "y": 1000,
            "frame_id": int(response.headers["X-Frame-Id"]),
        },
    )
    assert result.status_code == 200
    assert ("phone1", ("input", "touchscreen", "tap", "199", "399")) in fake_adb.calls


def test_foreign_origin_is_rejected_before_device(client, fake_adb):
    response = client.post(
        "/api/action", headers={"Origin": "https://foreign.example"}, json={"action": "home"}
    )
    assert response.status_code == 403
    assert not fake_adb.calls


def test_missing_request_token_is_rejected(client):
    client.headers.pop("X-Agent-CSRF")
    assert client.post("/api/stop", json={}).status_code == 403


def test_error_does_not_echo_secret_input(client):
    response = client.post(
        "/api/settings", json={"actor": {"api_key": "secret-key", "unexpected": "x"}}
    )
    assert response.status_code == 422
    assert "secret-key" not in response.text


def test_secret_is_masked_in_all_settings_responses(client):
    response = client.post(
        "/api/settings", json={"actor": {"api_key": "secret-key", "model": "test"}}
    )
    assert response.status_code == 200
    assert response.json()["actor"]["api_key_set"]
    assert "secret-key" not in response.text
    assert "secret-key" not in client.get("/api/settings").text


def test_invalid_text_never_reaches_device(client, fake_adb):
    response = client.post("/api/action", json={"action": "type", "text": "中文"})
    assert response.status_code == 422
    assert not fake_adb.calls


def test_ble_binding_requires_confirmation_and_selected_phone(client):
    response = client.post("/api/control/mode", json={"mode": "ble", "port": "COM5"})
    assert response.status_code == 422
    assert client.get("/api/status").json()["mode"] is None


def test_calibration_is_not_allowed_in_adb_mode(client):
    client.post("/api/devices/select", json={"serial": "phone1"})
    response = client.post(
        "/api/control/calibrate",
        json={
            "phone": "phone1",
            "width": 200,
            "height": 400,
            "counts_x": 800,
            "counts_y": 1200,
        },
    )
    assert response.status_code == 409
    assert not client.get("/api/settings").json()["ble_calibrations"]


@pytest.mark.parametrize("locate", [False, True])
async def test_manual_http_stop_reports_cancellation_and_allows_new_input(tmp_path, fake_adb, locate):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://localhost"
    ) as client:
        client.headers["X-Agent-CSRF"] = (await client.get("/api/session")).json()["csrf"]
        await client.post("/api/devices/select", json={"serial": "phone1"})
        started = asyncio.Event()
        calls = []
        controller = app.state.session.controller
        if locate:
            # Real session type gate, with isolated device IO and release.
            controller = BleController(None, "phone1", None)
            app.state.session.controller = controller
            async def release():
                return {"release": "hid_release_sent"}
            async def close():
                pass
            controller.stop, controller.close = release, close
        async def block(*args):
            calls.append(args)
            started.set()
            await asyncio.Event().wait()
        if locate:
            controller.locate = block
            path, payload = "/api/control/locate", {"x": 100, "y": 100}
        else:
            controller.execute = block
            path, payload = "/api/action", {"action": "swipe", "x1": 10, "y1": 20, "x2": 30, "y2": 40}
        request = asyncio.create_task(client.post(path, json=payload))
        await asyncio.wait_for(started.wait(), 2)
        stop = await client.post("/api/stop", json={})
        response = await asyncio.wait_for(request, 2)
        assert stop.status_code == 200
        assert stop.json()["release"] == ("hid_release_sent" if locate else "no_held_input")
        assert response.status_code == 409
        assert "observe the phone" in response.text
        assert len(calls) == 1
        async def complete(*args):
            calls.append(args)
            return {"ok": True}
        if locate:
            controller.locate = complete
        else:
            controller.execute = complete
        assert (await client.post(path, json=payload)).status_code == 200
        assert len(calls) == 2
