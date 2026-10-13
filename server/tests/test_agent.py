import asyncio
import json
from dataclasses import replace

import httpx
import pytest
from conftest import image_bytes

from android_agent.agent import TaskRunner
from android_agent.config import ModelSettings, Preferences
from android_agent.errors import AgentError, DeviceError
from android_agent.history import EventBus, TraceStore
from android_agent.llm import ModelClient, ModelReply, Usage
from android_agent.models import Action
from android_agent.screen import AdbScreen, decode_frame, validate_decision
from android_agent.session import DeviceSession

PLAN = {"plan": "1. Open Settings\n2. Check Wi-Fi"}
TAP = {"action": "tap", "x": 500, "y": 500, "reason": "Open Settings", "expected": "Settings visible"}
DONE = {"action": "done", "reason": "Settings visible", "answer": "Opened Settings"}
VERIFIED = {"confirmed": True, "evidence": "Settings title visible"}


class ScriptedModels:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []
        self.closed = 0

    def __call__(self, settings):
        outer = self
        class Client:
            async def chat(self, system, text, images):
                try:
                    payload = json.loads(text)
                except ValueError:
                    payload = text
                outer.calls.append((system, payload, images))
                if not outer.outputs:
                    raise AssertionError("Unexpected model call")
                output = outer.outputs.pop(0)
                if callable(output):
                    output = await output()
                if isinstance(output, BaseException):
                    raise output
                return ModelReply(json.dumps(output), Usage(50), 0.01)
            async def close(self):
                outer.closed += 1
        return Client()


async def runner(tmp_path, fake_adb, outputs, **limits):
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    models = ScriptedModels(outputs)
    task = TaskRunner(session, TraceStore(tmp_path), EventBus(), models, access_token="web-secret", settle_interval=0)
    prefs = Preferences(actor=ModelSettings(model="vision", api_key="model-secret"), **limits)
    await task.start("Open Settings", prefs)
    return task, session, models, prefs


async def finish(task):
    await asyncio.wait_for(asyncio.shield(task._task), 5)
    return task.public()


async def test_success_requires_separate_step_and_final_goal_checks(tmp_path, fake_adb):
    task, session, models, _ = await runner(tmp_path, fake_adb, [PLAN, TAP, VERIFIED, DONE, VERIFIED])
    snapshot = await finish(task)
    assert snapshot["state"] == "completed" and snapshot["actions"] == 1
    assert snapshot["model_calls"] == 5 and snapshot["tokens"] == 250
    assert len(models.calls[2][2]) == 2  # Independent before/after step verification.
    clean = decode_frame(fake_adb.png, "phone1", 1).jpeg
    assert models.calls[0][2] == [clean]  # Planner sees the unmodified phone.
    assert models.calls[1][2][0] != clean  # Actor alone sees coordinate guides.
    assert models.calls[2][2] == [clean, clean]
    assert models.calls[4][2] == [clean]
    assert models.calls[1][1]["screen"]["width"] == 200
    assert models.calls[1][1]["screen"]["height"] == 400
    assert models.calls[4][1] == {"kind": "goal", "goal": "Open Settings"}
    assert len(models.calls[4][2]) == 1
    assert models.closed == 2 and session._agent_owner is None
    assert any(args[:3] == ("input", "touchscreen", "tap") for _, args in fake_adb.calls)
    saved = await task.traces.read(task.id)
    assert saved["state"] == "completed"
    assert not list(task.traces.directory(task.id).glob("*.jpg"))
    assert task.images  # In-memory preview remains without disk screenshot opt-in.


async def test_actor_false_done_cannot_mark_task_complete(tmp_path, fake_adb):
    task, _, _, _ = await runner(tmp_path, fake_adb, [PLAN, DONE,
        {"confirmed": False, "evidence": "Home screen, no Settings title"}], max_failures=1)
    result = await finish(task)
    assert result["state"] == "failed" and result["actions"] == 0
    assert result["steps"][0]["status"] == "not_verified"


@pytest.mark.parametrize("confirmed", [True, False])
async def test_continuous_strokes_still_require_independent_goal_check(tmp_path, fake_adb, confirmed):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from android_agent.ble import BleController, Calibration
    path = {"action": "path", "points": [[300, 400], [400, 500], [600, 400]],
            "reason": "draw continuous curve", "expected": "one joined stroke"}
    circle = {"action": "circle", "x": 500, "y": 500, "r": 50,
              "reason": "draw circle", "expected": "closed round stroke"}
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    bridge = SimpleNamespace(connected=True, hid_ready=True, firmware="0.1.4", capabilities=["path"],
                             request=AsyncMock(return_value={}), stop=AsyncMock(return_value={"release": "hid_release_sent"}))
    session.controller = BleController(bridge, "phone1", Calibration(phone="phone1", width=200, height=400,
        counts_x=800, counts_y=1200, firmware="0.1.4"))
    models = ScriptedModels([PLAN, path, VERIFIED, circle, VERIFIED, DONE,
                             {"confirmed": confirmed, "evidence": "independent goal evidence"}])
    task = TaskRunner(session, TraceStore(tmp_path), EventBus(), models, settle_interval=0)
    await task.start("Draw the requested shapes", Preferences(actor=ModelSettings(model="vision", api_key="secret"), max_failures=1))
    result = await finish(task)
    assert result["state"] == ("completed" if confirmed else "failed")
    assert result["actions"] == 2 and result["model_calls"] == 7
    assert bridge.request.await_count == 2 and bridge.stop.await_count == 1
    assert all(call.kwargs["action"] == "path" for call in bridge.request.call_args_list)
    assert len(models.calls[2][2]) == 2 and len(models.calls[4][2]) == 2
    assert models.calls[6][1] == {"kind": "goal", "goal": "Draw the requested shapes"}


async def test_unsupported_model_action_never_reaches_device(tmp_path, fake_adb):
    task, _, _, _ = await runner(tmp_path, fake_adb, [PLAN, {**TAP, "x": True}], max_failures=1)
    assert (await finish(task))["state"] == "failed"
    assert not any("input" in args for _, args in fake_adb.calls)


@pytest.mark.parametrize("usage,budget,failures,expected_calls,expected_tokens,estimated", [
    ({"total_tokens": 321}, 100000, 3, 6, 993, 0),
    ({"total_tokens": 1100}, 1000, 3, 2, 1110, 0),
    (None, 100000, 1, 2, None, 1),
])
async def test_received_truncated_actions_never_execute_and_keep_usage(
        tmp_path, fake_adb, usage, budget, failures, expected_calls, expected_tokens, estimated):
    requests, clients = [], []
    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        planning = body["messages"][0]["content"].startswith("Plan")
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop" if planning else "length",
            "message": {"content": json.dumps(PLAN if planning else TAP)}}],
            "usage": {"total_tokens": 10} if planning else usage})
    def factory(settings):
        client = ModelClient(settings, httpx.MockTransport(handle))
        clients.append(client)
        return client
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    task = TaskRunner(session, TraceStore(tmp_path), EventBus(), factory, settle_interval=0)
    prefs = Preferences(actor=ModelSettings(model="vision"), max_total_tokens=budget, max_failures=failures)
    await task.start("Open Settings", prefs)
    result = await finish(task)
    assert result["state"] == "failed" and result["actions"] == 0
    assert len(requests) == result["model_calls"] == expected_calls
    assert result["uncertain_calls"] == 0 and result["estimated_calls"] == estimated
    if expected_tokens is not None:
        assert result["tokens"] == expected_tokens
    else:
        assert result["tokens"] > 4096
    assert "Token" in result["reason"] if budget == 1000 else "output limit" in result["reason"]
    assert not any("input" in args for _, args in fake_adb.calls)
    assert session._agent_owner is None and all(c.http.is_closed for c in clients)
    trace = (task.traces.directory(task.id) / "events.jsonl").read_text(encoding="utf-8")
    assert '"model_usage_unknown"' not in trace and '"model_usage"' in trace


async def test_changed_target_replans_before_input(tmp_path, fake_adb):
    async def change_screen():
        fake_adb.png = image_bytes(color="blue")
        return TAP
    task, _, _, _ = await runner(tmp_path, fake_adb, [PLAN, change_screen, PLAN,
        {"action": "fail", "reason": "New target needs user input"}])
    result = await finish(task)
    assert result["state"] == "failed" and result["actions"] == 0
    assert result["steps"][0]["status"] == "skipped_stale_screen"
    assert not any("input" in args for _, args in fake_adb.calls)


def test_freshness_checks_geometry_age_and_target_region():
    first = decode_frame(image_bytes(), "phone1", 1)
    action = Action(**TAP)
    validate_decision(first, first, action)
    for second in (decode_frame(image_bytes((400, 200)), "phone1", 2),
                   decode_frame(image_bytes(color="blue"), "phone1", 2)):
        with pytest.raises(AgentError):
            validate_decision(first, second, action)
    with pytest.raises(AgentError):
        validate_decision(replace(first, received=first.received - 61), first, action)


async def test_pause_cancels_model_allows_manual_and_resume_replans(tmp_path, fake_adb):
    started, cancelled = asyncio.Event(), asyncio.Event()
    async def blocked():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    task, session, models, prefs = await runner(tmp_path, fake_adb, [PLAN, blocked, PLAN, DONE, VERIFIED])
    await asyncio.wait_for(started.wait(), 3)
    with pytest.raises(DeviceError):
        await session.execute(Action(action="home"))
    with pytest.raises(DeviceError):
        await session.select("phone1")
    paused = await asyncio.wait_for(task.pause(), 3)
    assert paused["state"] == "paused" and cancelled.is_set() and models.closed == 2
    assert paused["uncertain_calls"] == 1 and paused["estimated_calls"] == 1
    await session.execute(Action(action="home"))
    with pytest.raises(DeviceError):
        await session.select("phone2")
    assert (await task.resume(prefs))["state"] == "planning"
    assert (await finish(task))["state"] == "completed"
    assert models.calls[2][0].startswith("Plan")
    assert task.actions == 0  # Canceled suggestion was never replayed.


async def test_pause_during_drag_releases_and_keeps_unknown_result(tmp_path, fake_adb):
    fake_adb.block_swipe = True
    swipe = {"action": "swipe", "x1": 500, "y1": 800, "x2": 500, "y2": 200,
             "duration_ms": 800, "reason": "Scroll", "expected": "More items visible"}
    task, session, _, _ = await runner(tmp_path, fake_adb, [PLAN, swipe])
    await asyncio.wait_for(fake_adb.swipe_started.wait(), 3)
    result = await asyncio.wait_for(task.pause(), 3)
    assert result["state"] == "paused" and task.actions == 1
    assert result["steps"][0]["status"] == "result_unknown"
    assert result["release"]["release"] == "up_event_sent"
    assert session._active is None
    await task.stop()


async def test_uncertain_device_result_pauses_without_retry_and_redacts_trace(tmp_path, fake_adb):
    async def fail(*args):
        raise DeviceError("Input result unknown model-secret web-secret")
    fake_adb.shell = fail
    task, _, models, _ = await runner(tmp_path, fake_adb, [PLAN, TAP])
    result = await finish(task)
    assert result["state"] == "paused" and result["actions"] == 1 and len(models.calls) == 2
    trace = (task.traces.directory(task.id) / "events.jsonl").read_text(encoding="utf-8")
    assert "model-secret" not in trace and "web-secret" not in trace
    assert "model-secret" not in json.dumps(result) and "[redacted]" in result["reason"]
    await task.stop()


async def test_action_limit_stops_before_another_input(tmp_path, fake_adb):
    task, _, _, _ = await runner(tmp_path, fake_adb, [PLAN, TAP, VERIFIED, TAP], max_steps=1)
    assert (await finish(task))["state"] == "failed"
    assert task.actions == 1 and "Action limit" in task.reason


async def test_budget_stops_further_model_calls(tmp_path, fake_adb):
    started = asyncio.Event()
    async def blocked():
        started.set()
        await asyncio.Event().wait()
    task, _, _, _ = await runner(tmp_path, fake_adb, [blocked])
    await started.wait()
    await task.pause()
    task.tokens = task.prefs.max_total_tokens
    with pytest.raises(AgentError, match="Token"):
        await task.resume(task.prefs)
    await task.stop()


async def test_black_screen_pauses_before_model_request(tmp_path, fake_adb):
    fake_adb.png = image_bytes(color="black")
    task, _, models, _ = await runner(tmp_path, fake_adb, [])
    assert (await finish(task))["state"] == "paused"
    assert not models.calls
    await task.stop()


async def test_active_timeout_cancels_request_and_releases_session(tmp_path, fake_adb):
    cancelled = asyncio.Event()
    async def blocked():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    task, session, _, _ = await runner(tmp_path, fake_adb, [blocked])
    task.prefs.max_seconds = 0.05  # Accelerate the same outer deadline used for real 10..7200s limits.
    result = await finish(task)
    assert result["state"] == "failed" and "time limit" in result["reason"]
    assert cancelled.is_set() and session._agent_owner is None


async def test_paused_time_excluded_and_step_images_bounded(tmp_path, fake_adb):
    started = asyncio.Event()
    async def blocked():
        started.set()
        await asyncio.Event().wait()
    task, _, _, _ = await runner(tmp_path, fake_adb, [blocked])
    await started.wait()
    await task.pause()
    elapsed = task.active_seconds
    await asyncio.sleep(0.03)
    assert task.active_seconds == elapsed
    await task.stop()
    outputs = [PLAN] + [item for _ in range(8) for item in (TAP, VERIFIED)] + [DONE, VERIFIED]
    task, _, _, _ = await runner(tmp_path, fake_adb, outputs)
    result = await finish(task)
    assert result["state"] == "completed" and len(task.images) == 12
    assert result["steps"][0]["before_available"] is False


async def test_screenshot_opt_in_and_clear_retains_disk_history(tmp_path, fake_adb):
    task, _, _, _ = await runner(tmp_path, fake_adb, [PLAN, DONE, VERIFIED], save_screenshots=True)
    await finish(task)
    task_id = task.id
    assert len(list(task.traces.directory(task_id).glob("*.jpg"))) == 1
    await task.clear()
    assert task.id is None and not task.images and not task.steps
    assert (await task.traces.read(task_id))["state"] == "completed"


@pytest.mark.parametrize("mode", ["adb", "hid_calibrated", "hid_uncalibrated", "hid_offline"])
async def test_actual_actor_request_only_examples_current_capabilities(tmp_path, fake_adb, mode):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from android_agent.agent import action_prompt
    from android_agent.ble import KEYS as HID_KEYS
    from android_agent.ble import BleController, Calibration
    from android_agent.llm import parse_decision
    from android_agent.models import KEYS

    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    if mode != "adb":
        bridge = SimpleNamespace(connected=True, hid_ready=mode != "hid_offline", firmware="0.1.4",
                                 capabilities=["tap", "swipe", "path", "type", "key", "wait"],
                                 stop=AsyncMock(return_value={"release": "hid_release_sent"}))
        calibration = Calibration(phone="phone1", width=200, height=400, counts_x=800,
                                  counts_y=1200, firmware="0.1.4") if mode == "hid_calibrated" else None
        session.controller = BleController(bridge, "phone1", calibration)
    capabilities = session.controller.capabilities
    models = ScriptedModels([PLAN, DONE, {"confirmed": False, "evidence": "Goal is absent"}])
    task = TaskRunner(session, TraceStore(tmp_path), EventBus(), models, settle_interval=0)
    if mode == "hid_offline":
        with pytest.raises(DeviceError, match="available controller"):
            await task.start("Open Settings", Preferences(actor=ModelSettings(model="vision")))
        assert not models.calls
        samples = [json.loads(line) for line in action_prompt([]).splitlines() if line.startswith("{")]
        assert {sample["action"] for sample in samples} == {"done", "fail", "replan"}
        for sample in samples:
            parse_decision(json.dumps(sample), [], set(HID_KEYS))
        return
    await task.start("Open Settings", Preferences(actor=ModelSettings(model="vision"), max_failures=1))
    result = await finish(task)
    system, payload, _ = models.calls[1]
    samples = [json.loads(line) for line in system.splitlines() if line.startswith("{")]
    meta = {"done", "fail", "replan"}
    assert {sample["action"] for sample in samples} == set(capabilities) | meta
    assert payload["capabilities"] == capabilities
    assert "home|back|recents" not in system
    for sample in samples:
        parse_decision(json.dumps(sample), capabilities, set(KEYS) if mode == "adb" else set(HID_KEYS))
        if sample["action"] in meta:
            assert set(sample) <= {"action", "reason", "answer"}
    assert result["state"] == "failed" and result["actions"] == 0
    assert models.calls[2][1] == {"kind": "goal", "goal": "Open Settings"}
    assert not any("input" in args for _, args in fake_adb.calls)
