import math
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from android_agent.ble import BleController, Calibration
from android_agent.controller import AdbController
from android_agent.errors import DeviceError, StaleFrameError
from android_agent.llm import parse_decision
from android_agent.models import Action
from android_agent.screen import decode_frame, validate_decision
from android_agent.usb import UsbController


@pytest.mark.parametrize("points", [[], [[1, 2]], [[1, 2]] * 21, [[True, 2], [3, 4]],
                                    [[1.2, 2], [3, 4]], [["1", 2], [3, 4]],
                                    [[-1, 2], [3, 4]], [[1, 1001], [3, 4]],
                                    [[1, 2, 3], [3, 4]], [{"x": 1, "y": 2}, [3, 4]]])
def test_path_rejects_invalid_points(points):
    with pytest.raises(ValidationError):
        Action(action="path", points=points)


@pytest.mark.parametrize("payload", [
    {"action": "circle", "x": 500, "y": 500, "r": True},
    {"action": "circle", "x": 500, "y": 500, "r": 0},
    {"action": "circle", "x": 500, "y": 500},
    {"action": "path", "points": [[1, 2], [3, 4]], "x": 1},
    {"action": "tap", "x": 1, "y": 2, "points": [[1, 2], [3, 4]]},
])
def test_drawing_fields_cannot_escape_action_schema(payload):
    with pytest.raises(ValidationError):
        Action.model_validate(payload)


@pytest.mark.parametrize("size", [(1080, 2400), (2400, 1080), (400, 400)])
def test_circle_is_closed_and_round_in_screen_pixels(size):
    points = Action(action="circle", x=500, y=500, r=100).stroke_points(*size)
    assert len(points) == 17 and points[0] == points[-1]
    radius = size[0] / 10
    for x, y in points:
        pixel_radius = math.hypot((x-500)*size[0]/1000, (y-500)*size[1]/1000)
        assert abs(pixel_radius-radius) <= math.hypot(*size)/2000


def test_circle_rejects_offscreen_extent_without_clipping():
    for action, size in [(Action(action="circle", x=50, y=500, r=100), (1080, 2400)),
                         (Action(action="circle", x=500, y=100, r=100), (2400, 1080))]:
        with pytest.raises(ValueError, match="outside"):
            action.stroke_points(*size)


class StrokeBridge:
    connected = hid_ready = True
    firmware = "0.1.4"
    capabilities = ["tap", "path", "type", "wait"]

    def __init__(self):
        self.request = AsyncMock(return_value={"elapsed_ms": 1500, "button_held_ms": 800})
        self.stop = AsyncMock(return_value={"release": "hid_release_sent"})
        self.close = AsyncMock()


def controller(kind=BleController, counts=(800, 1200)):
    bridge = StrokeBridge()
    calibration = Calibration(phone="phone1", width=200, height=400,
                              counts_x=counts[0], counts_y=counts[1], firmware=bridge.firmware)
    return kind(bridge, "phone1", calibration)


@pytest.mark.parametrize("kind", [BleController, UsbController])
async def test_stroke_is_one_mapped_command_with_transport_deadline(kind, fake_adb):
    control = controller(kind)
    frame = decode_frame(fake_adb.png, "phone1", 1)
    points = [[100, 200], [300, 250], [300, 250], [200, 400], [100, 200]]
    timing = await control.execute(Action(action="path", points=points, duration_ms=750), frame)
    control.bridge.request.assert_awaited_once_with(
        "action", timeout=60 if kind is BleController else 30, action="path",
        points=[(80, 240), (240, 300), (240, 300), (160, 480), (80, 240)], duration_ms=750)
    assert timing == {"elapsed_ms": 1500, "button_held_ms": 800}


async def test_circle_uses_same_single_path_command(fake_adb):
    control = controller()
    await control.execute(Action(action="circle", x=500, y=500, r=100),
                          decode_frame(fake_adb.png, "phone1", 1))
    args = control.bridge.request.call_args.kwargs
    assert args["action"] == "path" and len(args["points"]) == 17
    assert args["points"][0] == args["points"][-1]


@pytest.mark.parametrize("blocked", ["legacy", "uncalibrated", "version", "offline", "unsubscribed"])
async def test_drawing_capability_gate_sends_nothing(blocked, fake_adb):
    control = controller()
    if blocked == "legacy":
        control.bridge.capabilities = ["tap", "type", "wait"]
    elif blocked == "uncalibrated":
        control.calibration = None
    elif blocked == "version":
        control.bridge.firmware = "0.1.5"
    elif blocked == "offline":
        control.bridge.connected = False
    else:
        control.bridge.hid_ready = False
    assert "path" not in control.capabilities and "circle" not in control.capabilities
    with pytest.raises(DeviceError):
        await control.execute(Action(action="path", points=[[1, 2], [3, 4]]),
                              decode_frame(fake_adb.png, "phone1", 1))
    control.bridge.request.assert_not_called()


async def test_report_budget_and_offscreen_circle_rejected_before_input(fake_adb):
    control = controller(counts=(4000, 4000))
    frame = decode_frame(fake_adb.png, "phone1", 1)
    # Exactly 500 reports is allowed; one further count requires another report.
    await control.execute(Action(action="path", points=[[0, 0], [1000, 0]]), frame)
    control.bridge.request.reset_mock()
    with pytest.raises(DeviceError, match="movement limit"):
        await control.execute(Action(action="path", points=[[0, 0], [1000, 0], [1000, 1]]), frame)
    with pytest.raises(DeviceError, match="outside"):
        await control.execute(Action(action="circle", x=10, y=500, r=100), frame)
    control.bridge.request.assert_not_called()


def test_drawing_cannot_use_rotated_reference(fake_adb):
    reference = decode_frame(fake_adb.png, "phone1", 1)
    current = decode_frame(fake_adb.png, "phone1", 2)
    current = replace(current, width=current.height, height=current.width)
    with pytest.raises(StaleFrameError):
        validate_decision(reference, current, Action(action="path", points=[[1, 2], [3, 4]]))


def test_model_cannot_select_drawing_for_adb():
    from android_agent.llm import ModelProtocolError
    capabilities = AdbController(None, "phone1").capabilities
    assert "path" not in capabilities and "circle" not in capabilities
    with pytest.raises(ModelProtocolError):
        parse_decision('{"action":"path","points":[[1,2],[3,4]],"reason":"draw","expected":"line"}',
                       capabilities, set())


async def test_invalid_geometry_is_rejected_before_submission_callback(fake_adb):
    from android_agent.screen import AdbScreen
    from android_agent.session import DeviceSession
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    session.controller = controller()
    submitted = []
    with pytest.raises(DeviceError, match="outside"):
        await session._execute(Action(action="circle", x=0, y=500, r=100), on_submit=submitted.append)
    assert not submitted
    session.controller.bridge.request.assert_not_called()
