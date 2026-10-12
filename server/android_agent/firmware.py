"""Application-owned firmware maintenance jobs; esptool stays in a separate process."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
import shutil
import signal
import sys
import time
from importlib import metadata
from pathlib import Path

from .ble import BleController
from .board_info import PROFILES
from .errors import DeviceError
from .firmware_catalog import FirmwareCatalog, sha256
from .launcher import portable_root

PROTOCOL = "android-agent-firmware-v1"
# A source-only optional tool, never a frozen main-application dependency.
SOURCE_TOOL_DISTRIBUTION = "esptool"
ID = re.compile(r"[0-9a-f]{32}")
MAC = re.compile(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}")
DIGEST = re.compile(r"[0-9a-f]{64}")
log = logging.getLogger(__name__)


def default_catalog(settings) -> Path | None:
    root = portable_root()
    return settings.firmware_dir or (root / "firmware" if root else None)


class FirmwareTool:
    def __init__(self, settings):
        root = portable_root()
        if settings.firmware_tool:
            self.command = [str(settings.firmware_tool)]
        elif root:
            self.command = [str(root / "tools/firmware-tool/firmware-tool.exe")]
        else:
            worker = Path(__file__).resolve().parents[2] / "tools/firmware_worker.py"
            try:
                installed = metadata.version(SOURCE_TOOL_DISTRIBUTION) == "5.3.0"
            except metadata.PackageNotFoundError:
                installed = False
            self.command = [sys.executable, str(worker)] if worker.is_file() and installed else []

    @property
    def available(self) -> bool:
        return bool(self.command and (shutil.which(self.command[0]) or Path(self.command[0]).is_file()))

    async def _terminate(self, proc) -> None:
        if proc.returncode is not None and os.name == "nt":
            return
        if os.name == "nt":
            # This tool may create helpers. Stop this specific tool tree only.
            killer = await asyncio.create_subprocess_exec(
                str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/taskkill.exe"),
                "/PID", str(proc.pid), "/T", "/F",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            try:
                await asyncio.wait_for(killer.wait(), 10)
            except asyncio.TimeoutError:
                killer.kill()
                await killer.wait()
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        await proc.wait()

    async def run(self, operation: str, *args: str, timeout: float = 30) -> dict:
        if operation not in {"diagnose", "identify", "backup", "write"} or not self.available:
            raise DeviceError("Firmware tool missing; use the portable package or install ./server[firmware]")
        env = {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.command, operation, *args, env=env,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                **({"start_new_session": True} if os.name != "nt" else {}))
        except OSError as exc:
            raise DeviceError("Cannot start the firmware tool; check its installation") from exc

        async def drain(stream, limit):
            result = bytearray()
            overflow = False
            while chunk := await stream.read(8192):
                result.extend(chunk)
                if len(result) > limit:
                    overflow = True
                    del result[:-limit]
            return bytes(result), overflow

        out = asyncio.create_task(drain(proc.stdout, 65536))
        err = asyncio.create_task(drain(proc.stderr, 65536))
        async def collect():
            await proc.wait()
            output, overflow = await out
            await err
            return output, overflow
        try:
            output, overflow = await asyncio.wait_for(collect(), timeout)
            if proc.returncode or overflow:
                raise DeviceError("Firmware tool failed; check USB power, driver and port ownership. Writing may be incomplete; keep the backup.")
            result = json.loads(output)
            if not isinstance(result, dict) or result.get("protocol") != PROTOCOL or result.get("ok") is not True:
                raise DeviceError("Invalid firmware tool response; writing may be unverified")
            return result
        except asyncio.TimeoutError as exc:
            raise DeviceError("Firmware tool timed out; writing may be incomplete. Keep the backup and reconnect before retrying.") from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise DeviceError("Invalid firmware tool response; writing may be unverified") from exc
        finally:
            await self._terminate(proc)
            out.cancel()
            err.cancel()
            await asyncio.gather(out, err, return_exceptions=True)


def fingerprint(identity: dict) -> tuple:
    return identity.get("family"), identity.get("mac"), identity.get("flash_bytes")


def valid_identity(value: dict) -> dict:
    if (not isinstance(value, dict) or not isinstance(value.get("chip"), str)
            or not 1 <= len(value["chip"]) <= 200 or not isinstance(value.get("family"), str)
            or not re.fullmatch(r"esp32[a-z0-9]*", value["family"])
            or not isinstance(value.get("mac"), str) or not MAC.fullmatch(value["mac"])
            or (value.get("flash_bytes") is not None and (
                type(value["flash_bytes"]) is not int or not 1024 <= value["flash_bytes"] <= 134217728))):
        raise DeviceError("Board identity is incomplete; no flash was written")
    return value.copy()


class FirmwareManager:
    def __init__(self, settings, session, idle=lambda: True, *, tool=None, clock=time.monotonic):
        self.session, self.idle, self.clock = session, idle, clock
        self.tool = tool or FirmwareTool(settings)
        self.catalog = FirmwareCatalog(default_catalog(settings))
        self.directory = settings.data_dir / "firmware-backups"
        self.jobs_dir = settings.data_dir / "firmware-jobs"
        self.job = None
        self.task = None
        self.backups = {}

    async def initialize(self) -> None:
        def load():
            if not self.directory.is_dir():
                return {}
            found = {}
            for path in sorted(self.directory.glob("*.json"), reverse=True)[:100]:
                if not ID.fullmatch(path.stem) or path.is_symlink():
                    continue
                try:
                    if path.stat().st_size > 16384:
                        continue
                    data = json.loads(path.read_bytes())
                    if (data.get("id") != path.stem or data.get("profile") not in PROFILES
                            or type(data.get("flash_bytes")) is not int or data["flash_bytes"] not in {4194304, 8388608}
                            or not isinstance(data.get("sha256"), str) or not DIGEST.fullmatch(data["sha256"])):
                        continue
                    found[path.stem] = data
                except (OSError, ValueError, AttributeError):
                    continue
            return found
        self.backups = await asyncio.to_thread(load)

    @property
    def busy(self) -> bool:
        return self.task is not None and not self.task.done()

    def public(self) -> dict:
        data = {"tool_available": self.tool.available, "catalog": self.catalog.describe(),
                "busy": self.busy, "job": None, "backups": []}
        for entry in self.backups.values():
            data["backups"].append({key: entry.get(key) for key in ("id", "profile", "flash_bytes", "sha256", "created_at", "image_verified")})
        if self.job:
            job = self.job
            identity = job.get("identity")
            public_identity = {key: identity.get(key) for key in ("chip", "family", "flash_size", "flash_bytes", "pcb_model")} if identity else None
            if public_identity:
                public_identity["mac_suffix"] = identity["mac"][-8:]
            expired = job.get("expires", 0) <= self.clock()
            data["job"] = {"id": job["id"], "phase": job["phase"], "port": job["port"],
                           "identity": public_identity, "profile": job.get("profile"),
                           "compatible": job.get("compatible", []), "error": job.get("error", ""),
                           "backup": next((entry for entry in data["backups"] if entry["id"] == job["id"]), None),
                           "confirmation": job.get("confirmation", "") if job["phase"] == "ready" and not expired else "",
                           "expired": job["phase"] == "ready" and expired,
                           "image_verified": job.get("image_verified", False), "phone_input_verified": False,
                           "elapsed_seconds": round(self.clock() - job["started"] if self.busy else job.get("elapsed", 0), 1),
                           "cancel_allowed": self.busy and job["phase"] != "writing"}
        return data

    def _claim(self) -> None:
        self.session.guard_manual()
        if (self.busy or not self.idle() or self.session._agent_owner is not None
                or self.session._lock.locked() or self.session._stopping):
            raise DeviceError("Finish the current task, input or board operation before firmware maintenance")
        if isinstance(self.session.controller, BleController):
            raise DeviceError("Switch to ADB control before firmware maintenance")
        if not self.tool.available:
            raise DeviceError("Firmware tool missing; install ./server[firmware] or use the portable package")

    def _start(self, phase: str, work) -> dict:
        self._claim()
        job = self.job
        job["phase"], job["error"] = phase, ""
        job["started"] = self.clock()
        self.session._maintenance = job["id"]

        async def owned():
            try:
                await work()
            except asyncio.CancelledError:
                job["phase"], job["confirmation"] = "cancelled", ""
                raise
            except (OSError, ValueError, DeviceError) as exc:
                job["phase"], job["confirmation"] = "failed", ""
                job["error"] = str(exc) if isinstance(exc, DeviceError) else "Firmware assets or backup failed validation; no automatic retry. Keep any complete backup."
            except Exception:
                job["phase"], job["confirmation"] = "failed", ""
                job["error"] = "Firmware operation failed unexpectedly; result may be unknown. Keep the backup."
                log.error("Unexpected firmware operation failure", exc_info=False)
            finally:
                job["elapsed"] = self.clock() - job["started"]
                if self.session._maintenance == job["id"]:
                    self.session._maintenance = None
        pending = asyncio.create_task(owned(), name=f"firmware-{phase}")
        self.task = pending

        def finished(task):
            if not task.cancelled():
                task.exception()
            if self.task is task:
                self.task = None
        pending.add_done_callback(finished)
        return self.public()

    def identify(self, port: str) -> dict:
        self._claim()
        self.job = {"id": secrets.token_hex(16), "port": port, "started": self.clock(), "phase": "identifying"}
        job = self.job

        async def work():
            result = await self.tool.run("identify", "--port", port)
            job["identity"] = valid_identity(result.get("identity"))
            job["compatible"] = [item["profile"] for item in self.catalog.describe()["profiles"]
                                 if (item["family"], item["flash_bytes"]) == (job["identity"]["family"], job["identity"]["flash_bytes"])]
            job["phase"] = "identified"
        return self._start("identifying", work)

    def _job(self, job_id: str, phase: str) -> dict:
        if self.busy or not self.job or self.job["id"] != job_id or self.job["phase"] != phase:
            raise DeviceError("Firmware job changed; identify the board again before proceeding")
        return self.job

    @staticmethod
    def _identity_args(job: dict) -> list[str]:
        value = job["identity"]
        return ["--port", job["port"], "--family", value["family"], "--mac", value["mac"],
                "--flash-bytes", str(value["flash_bytes"])]

    def _save_record(self, record: dict) -> None:
        path = self.directory / f"{record['id']}.json"
        temporary = path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            temporary.chmod(0o600)
            json.dump(record, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)

    def backup(self, job_id: str, profile: str) -> dict:
        job = self._job(job_id, "identified")
        if profile not in job["compatible"]:
            raise DeviceError("Choose a firmware profile matching the identified chip and flash")
        job["profile"] = profile

        async def work():
            snapshot = self.jobs_dir / job_id / "catalog"
            job["manifest_sha256"] = await asyncio.to_thread(self.catalog.snapshot, profile, snapshot)
            self.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
            part = self.directory / f"{job_id}.part"
            result = await self.tool.run("backup", *self._identity_args(job), "--output", str(part), timeout=600)
            if fingerprint(valid_identity(result.get("identity"))) != fingerprint(job["identity"]):
                raise DeviceError("Board identity changed; no firmware was written")
            expected = job["identity"]["flash_bytes"]
            if part.is_symlink() or not part.is_file() or part.stat().st_size != expected:
                raise DeviceError("Incomplete flash backup; firmware write refused")
            digest = await asyncio.to_thread(sha256, part)
            if (type(result.get("size")) is not int or result["size"] != expected
                    or result.get("sha256") != digest):
                raise DeviceError("Incomplete or mismatched flash backup; firmware write refused")
            complete = self.directory / f"{job_id}.bin"
            part.rename(complete)
            record = {"id": job_id, "profile": profile, **job["identity"], "sha256": digest,
                      "created_at": time.time(), "image_verified": False}
            await asyncio.to_thread(self._save_record, record)
            self.backups[job_id] = record
            job["phase"], job["confirmation"], job["expires"] = "ready", secrets.token_urlsafe(32), self.clock() + 300
        return self._start("backing_up", work)

    def write(self, job_id: str, confirmation: str, confirm_overwrite: bool) -> dict:
        job = self._job(job_id, "ready")
        if (confirm_overwrite is not True or not confirmation or self.clock() >= job["expires"]
                or not secrets.compare_digest(confirmation, job["confirmation"])):
            raise DeviceError("Explicit overwrite confirmation expired or invalid; identify and back up again")
        self._claim()
        job["confirmation"] = ""  # Consume once before any await or process launch.

        async def work():
            record = self.backups[job_id]
            path = self.directory / f"{job_id}.bin"
            if path.is_symlink() or path.stat().st_size != record["flash_bytes"] or await asyncio.to_thread(sha256, path) != record["sha256"]:
                raise DeviceError("The complete backup changed; no firmware was written")
            snapshot = self.jobs_dir / job_id / "catalog"
            await asyncio.to_thread(FirmwareCatalog(snapshot).image_bytes, job["profile"], job["manifest_sha256"])
            result = await self.tool.run("write", *self._identity_args(job), "--backup", str(path),
                                         "--backup-sha256", record["sha256"], "--catalog", str(snapshot),
                                         "--profile", job["profile"], "--manifest-sha256", job["manifest_sha256"],
                                         "--confirm-overwrite", timeout=300)
            if (fingerprint(valid_identity(result.get("identity"))) != fingerprint(job["identity"])
                    or result.get("profile") != job["profile"] or result.get("image_verified") is not True):
                raise DeviceError("Firmware write result is unverified; keep the backup and inspect before retrying")
            job["image_verified"], job["phase"] = True, "written"
            await asyncio.to_thread(self._save_record, {**record, "image_verified": True})
            self.backups[job_id] = {**record, "image_verified": True}
        return self._start("writing", work)

    async def cancel(self, job_id: str) -> dict:
        if not self.job or self.job["id"] != job_id or not self.busy:
            raise DeviceError("No active firmware read operation to cancel")
        if self.job["phase"] == "writing":
            raise DeviceError("Writing and verification cannot be cancelled; keep USB connected")
        pending = self.task
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        return self.public()

    async def download(self, backup_id: str) -> tuple[bytes, str]:
        record = self.backups.get(backup_id)
        if not record or not ID.fullmatch(backup_id):
            raise DeviceError("Complete backup not found")
        path = self.directory / f"{backup_id}.bin"
        if path.is_symlink() or not path.resolve().is_relative_to(self.directory.resolve()):
            raise DeviceError("Invalid backup path")
        def read():
            with path.open("rb") as stream:
                return stream.read(record["flash_bytes"] + 1)
        data = await asyncio.to_thread(read)
        if len(data) != record["flash_bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise DeviceError("Backup is incomplete or changed")
        return data, record["sha256"]

    async def close(self) -> None:
        # A browser or graceful shutdown must never propagate cancellation into write.
        pending = self.task
        while pending and not pending.done():
            try:
                await asyncio.shield(pending)
            except asyncio.CancelledError:
                if pending.cancelled():
                    break
                # Graceful shutdown cancellation does not cancel the owned write.
                continue
