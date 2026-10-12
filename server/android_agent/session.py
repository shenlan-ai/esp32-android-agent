from __future__ import annotations

import asyncio

from .ble import BleController, Calibration, PointerProbe, SerialBridge
from .controller import AdbController
from .errors import DeviceError
from .models import Action
from .screen import AdbScreen, Frame, validate_decision
from .usb import UsbController


class DeviceSession:
    def __init__(self, adb, screen: AdbScreen):
        self.adb, self.screen = adb, screen
        self.controller = None
        self.serial: str | None = None
        self._lock = asyncio.Lock()
        self._epoch = 0
        self._active: asyncio.Task | None = None
        self._stop_lock = asyncio.Lock()
        self._stopping = False
        self._agent_owner = None
        self._agent_running = False
        self._maintenance: str | None = None

    def _guard_maintenance(self) -> None:
        if self._maintenance is not None:
            raise DeviceError("Wait for firmware maintenance to finish before device control")

    def guard_manual(self) -> None:
        self._guard_maintenance()
        if self._agent_owner is not None and self._agent_running:
            raise DeviceError("Pause the task and wait for input release before manual control")

    async def reserve(self, owner) -> None:
        self._guard_maintenance()
        if self._agent_owner is not None or self._lock.locked() or self._stopping:
            raise DeviceError("Stop the current operation or task before starting another task")
        async with self._lock:
            self._guard_maintenance()
            if not self.controller or not self.controller.capabilities:
                raise DeviceError("Connect the phone and an available controller first")
            self._agent_owner, self._agent_running = owner, True

    def suspend(self, owner) -> None:
        if self._agent_owner is owner:
            self._agent_running = False

    def activate(self, owner) -> None:
        self._guard_maintenance()
        if self._agent_owner is not owner or self._lock.locked() or self._stopping:
            raise DeviceError("Wait for manual input to finish before resuming")
        self._agent_running = True

    def release(self, owner) -> None:
        if self._agent_owner is owner:
            self._agent_owner, self._agent_running = None, False

    def _guard_selection(self, serial: str) -> None:
        self.guard_manual()
        if self._agent_owner is not None and serial != self.serial:
            raise DeviceError("Stop the paused task before selecting another phone")

    async def select(self, serial: str) -> None:
        self._guard_selection(serial)
        if self._lock.locked() or self._stopping:
            raise DeviceError("Stop the current operation before changing devices")
        devices = await self.adb.devices()
        if not any(d.serial == serial and d.state == "device" for d in devices):
            raise DeviceError(
                "Device is offline or unauthorized; unlock it and authorize this computer"
            )
        async with self._lock:
            self._guard_selection(serial)
            if self._agent_owner is not None and self.controller.mode != "adb":
                raise DeviceError("Reconnect the HID board without changing the task control mode")
            await self._close_controller()
            self._epoch += 1
            self.serial = serial
            self.screen.select(serial)
            self.controller = AdbController(self.adb, serial)

    async def _close_controller(self) -> None:
        if isinstance(self.controller, BleController):
            await self.controller.close()

    async def set_mode(
        self, mode: str, bridge: SerialBridge | None = None, calibration: Calibration | None = None
    ) -> None:
        self.guard_manual()
        if not self.serial:
            raise DeviceError("Select the phone before binding a HID board")
        if self._lock.locked() or self._stopping:
            raise DeviceError("Stop the current operation before switching control mode")
        async with self._lock:
            self.guard_manual()
            if self._agent_owner is not None and self.controller.mode != mode:
                raise DeviceError("Stop the paused task before changing its control mode")
            if mode not in {"adb", "ble", "usb"}:
                raise DeviceError("Choose an explicit supported control mode")
            if mode == "usb":
                devices = await self.adb.devices()
                if not any(d.serial == self.serial and d.state == "device" and d.transport == "wireless"
                           for d in devices):
                    raise DeviceError("USB HID requires an online wireless ADB phone; pair and connect it first")
            if mode != "adb" and not bridge:
                raise DeviceError("Connect a HID board first")
            if self.controller and getattr(self.controller, "bridge", None) is bridge and mode != "adb":
                await bridge.open()
                return
            self._epoch += 1
            await self._close_controller()
            self.controller = AdbController(self.adb, self.serial)
            if mode != "adb":
                # A failed explicit switch remains HID/unavailable, never silently ADB.
                controller = UsbController if mode == "usb" else BleController
                self.controller = controller(bridge, self.serial, calibration)
                await bridge.open()

    async def calibrate(self, calibration: Calibration) -> None:
        self.guard_manual()
        if self._lock.locked() or self._stopping:
            raise DeviceError("Stop the current operation before changing calibration")
        async with self._lock:
            self.guard_manual()
            if not isinstance(self.controller, BleController):
                raise DeviceError("Connect the HID board before calibrating")
            if not self.controller.bridge.connected or not self.controller.bridge.hid_ready:
                raise DeviceError(
                    "Connect the HID board to the phone before saving calibration"
                )
            frame = await self.screen.capture(force=True)
            calibration.check(frame)
            self.controller.calibration = calibration

    async def locate(self, probe: PointerProbe) -> dict:
        self.guard_manual()
        if self._stopping:
            raise DeviceError("Stop is still releasing input")
        epoch = self._epoch
        async with self._lock:
            self.guard_manual()
            if epoch != self._epoch or not isinstance(self.controller, BleController):
                raise DeviceError("HID calibration operation cancelled or unavailable")
            self._active = asyncio.current_task()
            try:
                return await self.controller.locate(probe)
            finally:
                self._active = None

    async def execute(self, action: Action, frame: Frame | None = None) -> dict:
        result, _ = await self._execute(action, frame)
        return result

    async def execute_agent(self, owner, action: Action, reference: Frame,
                            on_submit=None) -> tuple[dict, Frame]:
        return await self._execute(action, owner=owner, reference=reference, on_submit=on_submit)

    async def _execute(self, action: Action, frame: Frame | None = None,
                       owner=None, reference: Frame | None = None,
                       on_submit=None) -> tuple[dict, Frame]:
        def guard():
            self._guard_maintenance()
            if owner is None:
                self.guard_manual()
            elif self._agent_owner is not owner or not self._agent_running:
                raise DeviceError("Agent no longer owns the running device session")
        guard()
        if self._stopping:
            raise DeviceError("Stop is still releasing input; wait before operating")
        epoch = self._epoch
        async with self._lock:
            guard()
            if epoch != self._epoch:
                raise DeviceError("Operation cancelled by stop or device change")
            if not self.controller:
                raise DeviceError("Select a device first")
            self._active = asyncio.current_task()
            try:
                current = frame or await self.screen.capture(force=True)
                if current.serial != self.serial:
                    raise DeviceError("Screen does not belong to the selected device")
                if reference:
                    await asyncio.to_thread(validate_decision, reference, current, action)
                else:
                    self.screen.validate_reference(action.frame_id, current)
                if action.action not in self.controller.capabilities:
                    raise DeviceError("Action is unavailable for the selected controller")
                if isinstance(self.controller, BleController) and action.action in {"tap", "long_press", "swipe", "scroll"}:
                    if not self.controller.calibration:
                        raise DeviceError("Calibrate the HID mouse before coordinate actions")
                    self.controller.calibration.check(current)
                if on_submit:
                    on_submit(current)
                timing = await self.controller.execute(action, current)
                result = {"ok": True, "action": action.action, "frame_id": current.id}
                if timing:
                    result["execution"] = timing
                return result, current
            finally:
                self._active = None

    async def stop(self) -> dict:
        async with self._stop_lock:
            self._stopping = True
            self._epoch += 1
            try:
                task = self._active
                if task and task is not asyncio.current_task() and not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, DeviceError):
                        pass
                async with self._lock:
                    if self.controller:
                        return await self.controller.stop()
                    return {"cancelled": True, "release": "no_device"}
            finally:
                self._stopping = False

    async def close(self) -> None:
        await self.stop()
        await self._close_controller()
        await self.adb.close()
