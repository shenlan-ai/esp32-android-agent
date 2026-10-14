import asyncio
import base64
import io
import json
import sys
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock

import httpx
import pytest
from jsonschema import Draft202012Validator
from mcp import ClientSession, types
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.memory import create_connected_server_and_client_session
from PIL import Image

from android_agent.app import create_app
from android_agent.ble import CAPABILITIES, BleController, Calibration
from android_agent.ble import KEYS as HID_KEYS
from android_agent.config import RuntimeSettings
from android_agent.mcp import BridgeError, WorkbenchBridge, create_server, local_url
from android_agent.models import ACTION_EXAMPLES, ACTION_FIELDS, KEYS, Action
from android_agent.usb import UsbController


@pytest.mark.parametrize("url", [
    "http://example.com:8890", "https://localhost:8890", "http://127.0.0.1.evil",
    "http://user:password@localhost", "http://localhost/api", "http://localhost?token=secret",
    "http://localhost#fragment", "http://localhost:0", "http://localhost:99999",
])
def test_url_cannot_leak_credentials_or_access_remote_hosts(url):
    with pytest.raises(ValueError):
        local_url(url)


async def test_real_sdk_tool_contract_and_image(tmp_path, fake_adb):
    app = create_app(RuntimeSettings(data_dir=tmp_path, access_token="secret-test"), fake_adb)
    async with app.router.lifespan_context(app):
        await app.state.session.select("phone1")
        bridge = WorkbenchBridge("http://localhost", "secret-test", transport=httpx.ASGITransport(app))
        async with create_connected_server_and_client_session(create_server(bridge)) as client:
            tools = (await client.list_tools()).tools
            assert {t.name for t in tools} == {"android_status", "android_screenshot", "android_action", "android_stop"}
            schema = next(t for t in tools if t.name == "android_action").inputSchema["$defs"]["Action"]
            assert "frame_id" not in schema["properties"]
            assert set(schema["properties"]["action"]["enum"]) == set(ACTION_FIELDS) == set(ACTION_EXAMPLES)
            assert set(get_args(Action.model_fields["action"].annotation)) == set(ACTION_EXAMPLES)
            assert "continuously pressed" in schema["properties"]["points"]["description"]
            pair = schema["properties"]["points"]["anyOf"][0]["items"]
            assert "prefixItems" not in pair
            assert pair["items"] == {"type": "integer", "minimum": 0, "maximum": 1000}
            assert pair["minItems"] == pair["maxItems"] == 2
            validator = Draft202012Validator(next(t for t in tools if t.name == "android_action").inputSchema)
            validator.validate({"observation_id": "a" * 32, "action": ACTION_EXAMPLES["path"]})
            for invalid_point in (["10", 20], [10.5, 20], [True, 20], [10, 20, 30], [-1, 20]):
                assert list(validator.iter_errors({"observation_id": "a" * 32, "action": {"action": "path", "points": [invalid_point, [30, 40]]}}))
            assert "normalized x" in schema["properties"]["r"]["description"]
            assert set(schema["properties"]["key"]["anyOf"][0]["enum"]) == set(KEYS)
            status = await client.call_tool("android_status", {})
            assert status.structuredContent["mode"] == "adb"
            assert set(status.structuredContent["allowed_keys"]) == set(KEYS)
            assert set(status.structuredContent["action_examples"]) == set(ACTION_FIELDS) - {"path", "circle"}
            before = await client.call_tool("android_screenshot", {})
            assert not before.isError
            image = next(c for c in before.content if c.type == "image")
            assert image.mimeType == "image/jpeg"
            with Image.open(io.BytesIO(base64.b64decode(image.data))) as picture:
                assert picture.size == (200, 400)
            assert before.structuredContent is None
            metadata = json.loads(next(c.text for c in before.content if c.type == "text"))
            arguments = {"observation_id": metadata["observation_id"], "action": {"action": "tap", "x": 500, "y": 500}}
            result = await client.call_tool("android_action", arguments)
            assert not result.isError and result.structuredContent["ok"]
            duplicate = await client.call_tool("android_action", arguments)
            assert duplicate.isError and duplicate.structuredContent["code"] == "stale_observation"
            assert not (await client.call_tool("android_stop", {})).isError
            invalid = await client.call_tool("android_action", {"secret-input": "DO-NOT-ECHO"})
            assert invalid.isError
            assert "DO-NOT-ECHO" not in str(invalid)


@pytest.mark.parametrize(("name", "command"), [
    ("tap", ("input", "touchscreen", "tap", "100", "200")),
    ("long_press", ("input", "touchscreen", "swipe", "100", "200", "100", "200", "800")),
    ("swipe", ("input", "touchscreen", "swipe", "100", "319", "100", "80", "500")),
    ("scroll", ("input", "touchscreen", "swipe", "100", "200", "100", "104", "350")),
    ("type", ("input", "text", "ASCII%stext")),
    ("key", ("input", "keyevent", "66")),
    ("home", ("input", "keyevent", "3")),
    ("back", ("input", "keyevent", "4")),
    ("recents", ("input", "keyevent", "187")),
    ("wait", None),
])
async def test_every_adb_input_reaches_real_controller_through_sdk(tmp_path, fake_adb, name, command):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    async with app.router.lifespan_context(app):
        await app.state.session.select("phone1")
        bridge = WorkbenchBridge("http://localhost", transport=httpx.ASGITransport(app))
        async with create_connected_server_and_client_session(create_server(bridge)) as client:
            status = (await client.call_tool("android_status", {})).structuredContent
            action = status["action_examples"][name]
            shot = await client.call_tool("android_screenshot", {})
            observation_id = json.loads(next(c.text for c in shot.content if c.type == "text"))["observation_id"]
            result = await client.call_tool("android_action", {"observation_id": observation_id, "action": action})
            assert not result.isError and result.structuredContent["action"] == name
            inputs = [args for _, args in fake_adb.calls if args and args[0] == "input"]
            assert inputs == ([command] if command else [])
            assert (await client.call_tool("android_action", {"observation_id": observation_id, "action": action})).isError


@pytest.mark.parametrize("mode", ["ble", "usb"])
@pytest.mark.parametrize("name", ["path", "circle"])
async def test_continuous_drawing_through_sdk_and_real_hid_mapping(tmp_path, fake_adb, mode, name):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    board = SimpleNamespace(connected=True, hid_ready=True, capabilities=sorted(CAPABILITIES), firmware="0.1.4",
                            request=AsyncMock(return_value={"elapsed_ms": 1000}), stop=AsyncMock(return_value={"release": "test_release"}), close=AsyncMock())
    async with app.router.lifespan_context(app):
        session = app.state.session
        await session.select("phone1")
        calibration = Calibration(phone="phone1", width=200, height=400, counts_x=800, counts_y=1200, firmware="0.1.4")
        controller = (BleController if mode == "ble" else UsbController)(board, "phone1", calibration)
        session.controller = controller
        bridge = WorkbenchBridge("http://localhost", transport=httpx.ASGITransport(app))
        async with create_connected_server_and_client_session(create_server(bridge)) as client:
            status = (await client.call_tool("android_status", {})).structuredContent
            assert set(status["action_examples"]) == set(CAPABILITIES) | {"circle"}
            assert set(status["allowed_keys"]) == HID_KEYS
            assert set(status["action_rules"]) == {"path", "circle"}
            shot = await client.call_tool("android_screenshot", {})
            observation_id = json.loads(next(c.text for c in shot.content if c.type == "text"))["observation_id"]
            result = await client.call_tool("android_action", {"observation_id": observation_id, "action": status["action_examples"][name]})
            assert not result.isError and result.structuredContent["execution"]["elapsed_ms"] == 1000
            board.request.assert_awaited_once()
            sent = board.request.await_args.kwargs
            assert sent["action"] == "path" and sent["duration_ms"] == 500
            points = sent["points"]
            if name == "path":
                assert points == [(160, 360), (320, 360), (320, 600)]
            else:
                assert len(points) == 17 and points[0] == points[-1] == (440, 600)
                # A round 20px radius uses 50 normalized x / 25 normalized y.
                assert points[4] == (400, 630) and points[8] == (360, 600)
            assert not any(args and args[0] == "input" for _, args in fake_adb.calls)
            invalid = await client.call_tool("android_action", {"observation_id": observation_id, "action": {"action": "home"}})
            assert invalid.isError
            assert board.request.await_count == 1


@pytest.mark.parametrize("status", [401, 403, 409, 422, 500, 302])
async def test_http_errors_are_redacted_never_followed_or_retried(status):
    requests = []
    async def respond(request):
        requests.append(request.url.path)
        if request.url.path == "/api/session":
            return httpx.Response(200, json={"csrf": "csrf"})
        return httpx.Response(status, headers={"Location": "https://external.invalid/secret"}, json={"detail": "PRIVATE-TEXT-OR-TOKEN"})
    bridge = WorkbenchBridge("http://localhost", transport=httpx.MockTransport(respond))
    async with create_connected_server_and_client_session(create_server(bridge)) as client:
        result = await client.call_tool("android_action", {"observation_id": "a" * 32, "action": {"action": "home"}})
        assert result.isError and "PRIVATE-TEXT-OR-TOKEN" not in str(result)
        assert requests == ["/api/session", "/api/mcp/action"]


async def test_timeout_releases_without_replaying_action():
    paths = []
    async def respond(request):
        paths.append(request.url.path)
        if request.url.path == "/api/session":
            return httpx.Response(200, json={"csrf": "csrf"})
        if request.url.path == "/api/mcp/action":
            raise httpx.ReadTimeout("SECRET-URL", request=request)
        return httpx.Response(200, json={"release": "confirmed"})
    bridge = WorkbenchBridge("http://localhost", transport=httpx.MockTransport(respond))
    async with create_connected_server_and_client_session(create_server(bridge)) as client:
        result = await client.call_tool("android_action", {"observation_id": "a" * 32, "action": {"action": "home"}})
        assert result.isError and result.structuredContent["code"] == "transport_uncertain"
        assert "SECRET-URL" not in str(result)
        assert paths.count("/api/mcp/action") == 1 and paths.count("/api/stop") == 1


async def test_total_deadline_bounds_csrf_and_control_and_requests_stop():
    paths = []
    async def respond(request):
        paths.append(request.url.path)
        if request.url.path == "/api/mcp/action":
            await asyncio.sleep(10)
        return httpx.Response(200, json={"csrf": "csrf", "release": "confirmed"})
    bridge = WorkbenchBridge("http://localhost", transport=httpx.MockTransport(respond), timeout=0.05)
    try:
        with pytest.raises(BridgeError) as error:
            await asyncio.wait_for(bridge.invoke("android_action", {"observation_id": "a" * 32, "action": {"action": "home"}}), 2)
        assert error.value.code == "transport_uncertain"
        assert paths.count("/api/mcp/action") == 1 and paths.count("/api/stop") == 1
    finally:
        await bridge.close()


async def test_cancellation_releases_shared_controller(tmp_path, fake_adb):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    async with app.router.lifespan_context(app):
        await app.state.session.select("phone1")
        bridge = WorkbenchBridge("http://localhost", transport=httpx.ASGITransport(app))
        key = (await bridge.invoke("android_screenshot", {}))["observation_id"]
        fake_adb.block_swipe = True
        task = asyncio.create_task(bridge.invoke("android_action", {"observation_id": key, "action": {"action": "swipe", "x1": 10, "y1": 20, "x2": 30, "y2": 40}}))
        await asyncio.wait_for(fake_adb.swipe_started.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 2)
        assert app.state.session._active is None
        assert any("motionevent" in args and "UP" in args for _, args in fake_adb.calls)
        with pytest.raises(BridgeError):
            await bridge.invoke("android_action", {"observation_id": key, "action": {"action": "home"}})
        await bridge.close()


async def test_sdk_cancel_notification_releases_ongoing_input(tmp_path, fake_adb):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    async with app.router.lifespan_context(app):
        await app.state.session.select("phone1")
        bridge = WorkbenchBridge("http://localhost", transport=httpx.ASGITransport(app))
        async with create_connected_server_and_client_session(create_server(bridge)) as client:
            shot = await client.call_tool("android_screenshot", {})
            key = json.loads(next(c.text for c in shot.content if c.type == "text"))["observation_id"]
            fake_adb.block_swipe = True
            request_id = client._request_id
            task = asyncio.create_task(client.call_tool("android_action", {"observation_id": key, "action": {"action": "swipe", "x1": 10, "y1": 20, "x2": 30, "y2": 40}}))
            await asyncio.wait_for(fake_adb.swipe_started.wait(), 2)
            # MCP cancellation is an explicit protocol notification; cancelling a
            # Python SDK await alone does not send it (SDK1.30.0).
            await client.send_notification(types.ClientNotification(
                types.CancelledNotification(params=types.CancelledNotificationParams(
                    requestId=request_id, reason="acceptance cancellation"
                ))
            ))
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            # Client cancellation notification travels through the real MCP session.
            async def released():
                while app.state.session.controller._last_touch is not None:
                    await asyncio.sleep(0.01)
            await asyncio.wait_for(released(), 2)
            assert any("motionevent" in args and "UP" in args for _, args in fake_adb.calls)


async def test_stdio_initialization_and_errors_without_running_workbench(tmp_path):
    # Actual subprocess, newline JSON-RPC and SDK initialization (not an in-process mock).
    import socket
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    params = StdioServerParameters(command=sys.executable, args=["-m", "android_agent.mcp", "--url", f"http://127.0.0.1:{port}"])
    async with _stdio(params) as client:
        initial = await client.initialize()
        assert "screenshot before EVERY" in initial.instructions
        assert len((await client.list_tools()).tools) == 4
        response = await client.call_tool("android_status", {})
        assert response.isError and response.structuredContent["code"] == "transport_uncertain"


@asynccontextmanager
async def _stdio(params):
    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
        yield client
