from __future__ import annotations

import asyncio

from .controller import AdbController
from .errors import DeviceError
from .models import Action
from .screen import AdbScreen, Frame


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

    async def select(self, serial: str) -> None:
        if self._lock.locked() or self._stopping:
            raise DeviceError("Stop the current operation before changing devices")
        devices = await self.adb.devices()
        if not any(d.serial == serial and d.state == "device" for d in devices):
            raise DeviceError(
                "Device is offline or unauthorized; unlock it and authorize this computer"
            )
        async with self._lock:
            self._epoch += 1
            self.serial = serial
            self.screen.select(serial)
            self.controller = AdbController(self.adb, serial)

    async def execute(self, action: Action, frame: Frame | None = None) -> dict:
        if self._stopping:
            raise DeviceError("Stop is still releasing input; wait before operating")
        epoch = self._epoch
        async with self._lock:
            if epoch != self._epoch:
                raise DeviceError("Operation cancelled by stop or device change")
            if not self.controller:
                raise DeviceError("Select a device first")
            self._active = asyncio.current_task()
            try:
                current = frame or await self.screen.capture(force=True)
                if current.serial != self.serial:
                    raise DeviceError("Screen does not belong to the selected device")
                self.screen.validate_reference(action.frame_id, current)
                await self.controller.execute(action, current)
                return {"ok": True, "action": action.action, "frame_id": current.id}
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
        await self.adb.close()
