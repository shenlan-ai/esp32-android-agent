from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool


class PortSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    port: str = Field(min_length=1, max_length=200)


class FirmwareJobSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str = Field(pattern=r"^[0-9a-f]{32}$")


class FirmwareBackupSelection(FirmwareJobSelection):
    profile: str = Field(min_length=1, max_length=64)


class FirmwareWriteConfirmation(FirmwareJobSelection):
    confirmation: str = Field(min_length=1, max_length=100)
    confirm_overwrite: StrictBool = False


def register_firmware_routes(app: FastAPI, ports) -> None:
    @app.get("/api/firmware")
    async def status(request: Request):
        return request.app.state.firmware.public()

    @app.post("/api/firmware/identify")
    async def identify(payload: PortSelection, request: Request):
        if payload.port not in {port["port"] for port in ports()}:
            raise ValueError("Choose a connected ESP USB/UART serial port")
        return request.app.state.firmware.identify(payload.port)

    @app.post("/api/firmware/backup")
    async def backup(payload: FirmwareBackupSelection, request: Request):
        return request.app.state.firmware.backup(payload.job_id, payload.profile)

    @app.post("/api/firmware/write")
    async def write(payload: FirmwareWriteConfirmation, request: Request):
        return request.app.state.firmware.write(payload.job_id, payload.confirmation, payload.confirm_overwrite)

    @app.post("/api/firmware/cancel")
    async def cancel(payload: FirmwareJobSelection, request: Request):
        return await request.app.state.firmware.cancel(payload.job_id)

    @app.get("/api/firmware/backups/{backup_id}")
    async def download(backup_id: str, request: Request):
        content, digest = await request.app.state.firmware.download(backup_id)
        return Response(content, media_type="application/octet-stream", headers={
            "Content-Disposition": f'attachment; filename="esp32-backup-{backup_id}.bin"',
            "X-Firmware-SHA256": digest})
