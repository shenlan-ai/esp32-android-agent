# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 ESP32 Android Agent contributors.
# Separate firmware-tool process using esptool; see tools/LICENSE.
"""Limited firmware worker. Never imported by the MIT application process."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# The source worker is usable after installing ./server[firmware]. PyInstaller
# bundles just these dependency-free shared modules, not the server itself.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from android_agent.board_info import PROFILES, parse_chip  # noqa: E402
from android_agent.firmware_catalog import FirmwareCatalog, sha256  # noqa: E402

PROTOCOL = "android-agent-firmware-v1"
BACKUP_CHUNK_BYTES = 256 * 1024


def identity(esp, api) -> dict:
    size = api.cmds.detect_flash_size(esp)
    raw_mac = esp.read_mac()
    if not isinstance(raw_mac, (list, tuple)) or len(raw_mac) != 6 or any(type(n) is not int or not 0 <= n <= 255 for n in raw_mac):
        raise ValueError("The board has no valid MAC identity")
    mac = ":".join(f"{part:02x}" for part in raw_mac)
    report = parse_chip(f"Chip type: {esp.get_chip_description()}\nFlash size: {size}\nMAC: {mac}")
    # The chip family comes from esptool's actual selected ROM class, not a PCB label.
    family = esp.CHIP_NAME.lower().replace("-", "")
    return {**report, "family": family, "mac": mac}


def check_identity(actual: dict, args) -> None:
    if (actual.get("family") != args.family or actual.get("flash_bytes") != args.flash_bytes
            or actual.get("mac") != args.mac):
        raise ValueError("Board identity changed; no flash was written")


def perform(args, api, diagnostic: dict | None = None) -> dict:
    diagnostic = diagnostic if diagnostic is not None else {}

    def stage(value: str, **fields) -> None:
        diagnostic.clear()
        diagnostic.update(stage=value, **fields)

    stage("validate")
    if args.operation not in {"diagnose", "identify", "backup", "write"}:
        raise ValueError("Unsupported firmware operation")
    if api.__version__ != "5.3.0":
        raise ValueError("Firmware worker requires esptool 5.3.0")
    if args.operation == "diagnose":
        return {"ok": True, "protocol": PROTOCOL, "esptool": api.__version__, "device_used": False}
    profile = None
    images = None
    if not args.port:
        raise ValueError("A serial port is required")
    if args.operation != "identify":
        if (args.family not in {"esp32", "esp32s3"} or args.flash_bytes not in {4194304, 8388608}
                or not args.mac or not re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", args.mac)):
            raise ValueError("Expected board identity is required")
    if args.operation == "write":
        if not args.confirm_overwrite or not args.catalog or not args.profile or not args.manifest_sha256:
            raise ValueError("Explicit overwrite confirmation and prepared firmware are required")
        if not args.backup or not args.backup_sha256:
            raise ValueError("A complete verified flash backup is required")
        if (args.backup.is_symlink() or args.backup.stat().st_size != args.flash_bytes
                or sha256(args.backup) != args.backup_sha256):
            raise ValueError("The backup is incomplete or changed")
        profile, images = FirmwareCatalog(args.catalog).image_bytes(args.profile, args.manifest_sha256)
        if profile["family"] != args.family or profile["flash_bytes"] != args.flash_bytes:
            raise ValueError("Prepared firmware does not match the expected board")
    if args.operation == "backup" and not args.output:
        raise ValueError("A new backup output path is required")

    # Exactly one serial connection owns fingerprint checks AND the operation.
    # A disconnect cannot reopen a newly assigned COM port and replay a write.
    stage("connect")
    with api.detect_chip(port=args.port, baud=115200, connect_attempts=3) as rom:
        try:
            # Direct detect_chip leaves pyserial's read timeout at None. Commands
            # restore it before run_stub's raw handshake read, which must be bounded.
            stage("identify")
            rom._port.timeout = api.loader.DEFAULT_TIMEOUT
            api.cmds.attach_flash(rom)
            observed = identity(rom, api)
            if args.operation == "identify":
                return {"ok": True, "protocol": PROTOCOL, "identity": observed}
            check_identity(observed, args)
            stage("stub")
            esp = rom.run_stub()
            if args.operation == "backup":
                # Long reads use the initial conservative rate, without a failed-read retry.
                data = bytearray()
                for offset in range(0, args.flash_bytes, BACKUP_CHUNK_BYTES):
                    length = min(BACKUP_CHUNK_BYTES, args.flash_bytes - offset)
                    stage("read", completed_bytes=len(data), total_bytes=args.flash_bytes)
                    # Each official read verifies its transport digest. Keep the
                    # connection and abort a failed range rather than replaying it.
                    chunk = api.cmds.read_flash(esp, offset, length, no_progress=True)
                    if not isinstance(chunk, bytes) or len(chunk) != length:
                        raise ValueError("Incomplete flash backup")
                    data.extend(chunk)
                stage("save")
                with args.output.open("xb") as stream:
                    args.output.chmod(0o600)
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                return {"ok": True, "protocol": PROTOCOL, "identity": observed,
                        "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            stage("write")
            esp.change_baud(460800)
            api.cmds.write_flash(esp, images, flash_mode=profile["flash_mode"],
                                 flash_freq=profile["flash_freq"], flash_size=observed["flash_size"])
            # verify_flash applies the same bootloader-header adjustments as write_flash.
            stage("verify")
            api.cmds.verify_flash(esp, images, flash_mode=profile["flash_mode"],
                                  flash_freq=profile["flash_freq"], flash_size=observed["flash_size"])
            return {"ok": True, "protocol": PROTOCOL, "identity": observed,
                    "profile": args.profile, "image_verified": True, "phone_input_verified": False}
        finally:
            try:
                rom.hard_reset()
            except Exception:
                # Preserve the actual operation failure; closing the connection still follows.
                pass


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("operation", choices=("diagnose", "identify", "backup", "write"))
    result.add_argument("--port")
    result.add_argument("--family")
    result.add_argument("--mac")
    result.add_argument("--flash-bytes", type=int)
    result.add_argument("--output", type=Path)
    result.add_argument("--backup", type=Path)
    result.add_argument("--backup-sha256")
    result.add_argument("--catalog", type=Path)
    result.add_argument("--profile", choices=tuple(PROFILES))
    result.add_argument("--manifest-sha256")
    result.add_argument("--confirm-overwrite", action="store_true")
    return result


def failure_result(operation: str, diagnostic: dict, exc: Exception) -> dict:
    # Exception text is inspected only to select fixed codes, never forwarded.
    message = str(exc).lower()
    if isinstance(exc, TimeoutError) or "timed out waiting for packet" in message:
        reason = "timeout"
    elif "packet content transfer stopped" in message:
        reason = "packet_transfer_stopped"
    elif "digest mismatch" in message:
        reason = "digest_mismatch"
    elif isinstance(exc, OSError):
        reason = "io_error"
    else:
        reason = "operation_failed"
    failure = {"stage": diagnostic.get("stage", "unknown"), "reason": reason}
    if failure["stage"] == "read":
        failure.update({key: diagnostic[key] for key in ("completed_bytes", "total_bytes")})
    return {"ok": False, "protocol": PROTOCOL, "error": "operation_failed",
            "operation": operation, "failure": failure}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parser().parse_args()
    diagnostic = {}
    try:
        # esptool's human progress belongs on stderr; stdout is one JSON result.
        with contextlib.redirect_stdout(sys.stderr):
            import esptool
            import esptool.cmds
            result = perform(args, esptool, diagnostic)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except Exception as exc:
        print(f"Firmware worker operation failed: {type(exc).__name__}", file=sys.stderr)
        print(json.dumps(failure_result(args.operation, diagnostic, exc)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
