import asyncio
import base64
import io
import time
from dataclasses import replace

import httpx
import pytest
from conftest import image_bytes
from fastapi.testclient import TestClient
from PIL import Image

from android_agent.app import create_app
from android_agent.config import RuntimeSettings
from android_agent.errors import DeviceError
from android_agent.mcp_api import Observation


@pytest.fixture
def client(tmp_path, fake_adb):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    with TestClient(app, base_url="http://localhost") as client:
        client.headers["x-agent-csrf"] = client.get("/api/session").json()["csrf"]
        client.post("/api/devices/select", json={"serial": "phone1"})
        yield client


def observe(client):
    response = client.post("/api/mcp/screenshot", json={})
    assert response.status_code == 200
    return response.json()["observation_id"]


def send(client, key, action=None):
    return client.post("/api/mcp/action", json={"observation_id": key,
                                               "action": action or {"action": "tap", "x": 1000, "y": 1000}})


def inputs(adb):
    return [args for _, args in adb.calls if args and args[0] == "input"]


def test_image_and_capabilities_are_private_and_coordinate_mapping_exact(client, fake_adb):
    status = client.get("/api/mcp/status")
    assert status.json()["mode"] == "adb"
    assert "tap" in status.json()["capabilities"]
    assert "phone1" not in status.text
    screenshot = client.post("/api/mcp/screenshot", json={}).json()
    with Image.open(io.BytesIO(base64.b64decode(screenshot["image_base64"]))) as picture:
        assert picture.size == (200, 400)
        assert picture.format == "JPEG"
    assert screenshot["frame"]["width"] == 200
    assert send(client, screenshot["observation_id"]).status_code == 200
    assert ("input", "touchscreen", "tap", "199", "399") in inputs(fake_adb)
    assert send(client, screenshot["observation_id"]).status_code == 409
    assert len(inputs(fake_adb)) == 1


@pytest.mark.parametrize("change", ["stop", "selection", "mode", "manual", "calibration_epoch"])
def test_session_changes_invalidate_observation(client, fake_adb, change):
    key = observe(client)
    if change == "stop":
        client.post("/api/stop")
    elif change == "selection":
        client.post("/api/devices/select", json={"serial": "phone1"})
    elif change == "mode":
        client.post("/api/control/mode", json={"mode": "adb"})
    elif change == "manual":
        client.post("/api/action", json={"action": "home"})
    else:
        client.app.state.session._epoch += 1
    before = len(inputs(fake_adb))
    assert send(client, key).status_code == 409
    assert len(inputs(fake_adb)) == before


@pytest.mark.parametrize("change", ["rotation", "scene", "expiration", "black"])
def test_stale_screen_never_issues_input(client, fake_adb, change):
    key = observe(client)
    if change == "rotation":
        fake_adb.png = image_bytes((400, 200))
    elif change == "scene":
        fake_adb.png = image_bytes(color="red")
    elif change == "black":
        fake_adb.png = image_bytes(color="black")
    else:
        store = client.app.state.mcp_observations
        old = store.frames[key]
        store.frames[key] = Observation(replace(old.frame, received=time.monotonic() - 61), old.binding)
    assert send(client, key).status_code == 409
    assert not inputs(fake_adb)


def test_preview_does_not_evict_mcp_reference_but_store_is_bounded(client, fake_adb):
    key = observe(client)
    for _ in range(14):
        client.app.state.session.screen.frame = None
        assert client.get("/api/frame.png").status_code == 200
    assert send(client, key).status_code == 200
    first = observe(client)
    for _ in range(8):
        observe(client)
    assert len(client.app.state.mcp_observations.frames) == 8
    assert send(client, first).status_code == 409
    assert len(inputs(fake_adb)) == 1


@pytest.mark.parametrize("action", [
    {"action": "tap", "x": True, "y": 2},
    {"action": "tap", "x": 1.2, "y": 2},
    {"action": "tap", "x": 1001, "y": 2},
    {"action": "type", "text": "中文"},
    {"action": "type", "text": "hello\n"},
    {"action": "home", "text": "extra"},
    {"action": "home", "frame_id": 1},
    {"action": "circle", "x": 500, "y": 500, "r": 100},
    {"action": "path", "points": [["10", 20], [30, 40]]},
    {"action": "path", "points": [[10.5, 20], [30, 40]]},
    {"action": "path", "points": [[True, 20], [30, 40]]},
    {"action": "path", "points": [[10, 20, 30], [30, 40]]},
    {"action": "path", "points": [[-1, 20], [30, 40]]},
])
def test_invalid_and_unsupported_actions_never_reach_phone(client, fake_adb, action):
    assert send(client, observe(client), action).status_code in {409, 422}
    assert not inputs(fake_adb)


@pytest.mark.parametrize("guard", ["task", "maintenance"])
def test_existing_owner_blocks_mcp(client, fake_adb, guard):
    key = observe(client)
    session = client.app.state.session
    if guard == "task":
        session._agent_owner, session._agent_running = object(), True
    else:
        session._maintenance = "test"
    assert send(client, key).status_code == 409
    assert not inputs(fake_adb)
    session._agent_owner, session._agent_running, session._maintenance = None, False, None


@pytest.mark.parametrize("failure", ["black", "disconnect", "corrupt"])
def test_capture_failure_invalidates_releases_and_can_recover(client, fake_adb, failure):
    key = observe(client)
    original_run = fake_adb.run
    if failure == "black":
        fake_adb.png = image_bytes(color="black")
    elif failure == "corrupt":
        fake_adb.png = b"broken"
    else:
        async def offline(*args, **kwargs):
            raise DeviceError("device-private-serial offline")
        fake_adb.run = offline
    assert client.post("/api/mcp/screenshot").status_code == 409
    assert not client.app.state.mcp_observations.frames
    assert send(client, key).status_code == 409
    fake_adb.run, fake_adb.png = original_run, image_bytes()
    assert send(client, observe(client)).status_code == 200


async def test_competing_observations_and_stop_cancel_queue(tmp_path, fake_adb):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://localhost"
    ) as client:
        client.headers["x-agent-csrf"] = (await client.get("/api/session")).json()["csrf"]
        await client.post("/api/devices/select", json={"serial": "phone1"})
        keys = [(await client.post("/api/mcp/screenshot")).json()["observation_id"] for _ in range(2)]
        async def tap(key):
            return await client.post("/api/mcp/action", json={"observation_id": key, "action": {"action": "tap", "x": 500, "y": 500}})
        results = await asyncio.gather(*(tap(k) for k in keys))
        assert sorted(r.status_code for r in results) == [200, 409]
        assert len(inputs(fake_adb)) == 1
        key = (await client.post("/api/mcp/screenshot")).json()["observation_id"]
        fake_adb.block_swipe = True
        first = asyncio.create_task(client.post("/api/mcp/action", json={"observation_id": key, "action": {"action": "swipe", "x1": 20, "y1": 20, "x2": 80, "y2": 80}}))
        await asyncio.wait_for(fake_adb.swipe_started.wait(), 2)
        queued = asyncio.create_task(tap(key))
        await asyncio.sleep(0)
        stop = await client.post("/api/stop")
        responses = await asyncio.wait_for(asyncio.gather(first, queued), 2)
        assert all(r.status_code == 409 for r in responses)
        assert stop.json()["release"] == "up_event_sent"
        assert len([x for x in inputs(fake_adb) if "tap" in x]) == 1


def test_bridge_endpoints_obey_token_csrf_and_origin(tmp_path, fake_adb):
    app = create_app(RuntimeSettings(data_dir=tmp_path, access_token="private-token"), fake_adb)
    with TestClient(app, base_url="http://localhost") as client:
        assert client.get("/api/mcp/status").status_code == 401
        client.headers["x-agent-token"] = "private-token"
        assert client.post("/api/mcp/screenshot").status_code == 403
        client.headers["x-agent-csrf"] = client.get("/api/session").json()["csrf"]
        assert client.post("/api/mcp/screenshot", headers={"Origin": "https://foreign.example"}).status_code == 403
        assert "private-token" not in client.get("/api/mcp/status").text


def test_selected_offline_phone_has_no_advertised_input(client, fake_adb):
    fake_adb.entries = []
    status = client.get("/api/mcp/status").json()
    assert status["selected"] and not status["connected"]
    assert status["capabilities"] == []
    assert status["allowed_keys"] == []
    assert status["action_examples"] == {}
    assert status["action_rules"] == {}


@pytest.mark.parametrize("limit", ["not_ready", "not_calibrated", "maintenance"])
def test_hid_discovery_never_advertises_unavailable_inputs(client, limit):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from android_agent.ble import CAPABILITIES, KEYS, BleController, Calibration

    board = SimpleNamespace(connected=True, hid_ready=limit != "not_ready", capabilities=sorted(CAPABILITIES), firmware="0.1.4",
                            stop=AsyncMock(return_value={"release": "test_release"}), close=AsyncMock())
    calibration = None if limit == "not_calibrated" else Calibration(
        phone="phone1", width=200, height=400, counts_x=800, counts_y=1200, firmware="0.1.4")
    client.app.state.session.controller = BleController(board, "phone1", calibration)
    if limit == "maintenance":
        client.app.state.firmware.task = SimpleNamespace(done=lambda: False)
    try:
        status = client.get("/api/mcp/status").json()
    finally:
        client.app.state.firmware.task = None
    expected = {"type", "key", "wait"} if limit == "not_calibrated" else set()
    assert set(status["capabilities"]) == set(status["action_examples"]) == expected
    assert set(status["allowed_keys"]) == (KEYS if expected else set())
    assert status["action_rules"] == {}
