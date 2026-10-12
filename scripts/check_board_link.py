"""Verify an explicitly selected BLE bridge without sending HID actions."""
from __future__ import annotations

import argparse
import asyncio
import json
import time

import serial
from android_agent.ble import SerialBridge


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def exchange(device: serial.Serial, payload: dict | bytes, command_id: int) -> dict:
    data = payload if isinstance(payload, bytes) else (
        json.dumps(payload, separators=(",", ":")) + "\n"
    ).encode()
    require(device.write(data) == len(data), "Incomplete serial write")
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        line = device.readline(1026)
        try:
            response = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(response, dict) and response.get("id") == command_id:
            require(response.get("v") == 1, "Invalid response version")
            return response
    raise RuntimeError(f"No response to command {command_id}")


def protocol_checks(port: str) -> dict:
    checks: list[str] = []
    device = serial.Serial(port=None, baudrate=115200, timeout=0.1, write_timeout=0.5)
    device.dtr = False
    device.rts = False
    device.port = port
    try:
        device.open()
        time.sleep(1.5)
        device.reset_input_buffer()
        hello = exchange(device, {"v": 1, "id": 1, "op": "hello"}, 1)
        require(hello.get("status") == "hello" and hello.get("chip") == "esp32",
                "Not a classic ESP32 BLE bridge")
        session = hello.get("session")
        require(isinstance(session, str) and len(session) == 32, "Invalid session")
        require(hello.get("ble_name") == "Android Agent BLE", "Unexpected BLE name")
        checks.append("hello_chip_session")

        def request(command_id: int, op: str, **args) -> dict:
            return exchange(device, {"v": 1, "session": session,
                                    "id": command_id, "op": op, **args}, command_id)

        status = request(2, "status")
        require(status.get("status") == "ready" and
                type(status.get("ble_connected")) is bool, "Invalid status")
        checks.append("status")
        invalid = request(3, "status", v=2)
        require(invalid.get("error") == "protocol_version", "Wrong version accepted")
        checks.append("version_rejected")
        stale = request(4, "status", session="stale-session")
        require(stale.get("error") == "stale_session", "Old session accepted")
        checks.append("stale_session_rejected")
        invalid_json = exchange(device, b"{invalid-json}\n", 0)
        require(invalid_json.get("error") == "invalid_json", "Invalid JSON accepted")
        checks.append("invalid_json_rejected")
        overlong = b"x" * 1100 + b"\n"
        require(device.write(overlong) == len(overlong), "Incomplete oversized probe")
        require(request(5, "status").get("status") == "ready", "Line limit broke parser")
        checks.append("oversized_line_recovery")

        stopped = request(6, "stop")
        require(stopped.get("status") == "stopped" and
                type(stopped.get("release_sent")) is bool, "Invalid stop response")
        if not stopped.get("ble_connected"):
            require(stopped["release_sent"] is False, "False phone release confirmation")
        checks.append("stop_honest_release")
        for _ in range(4):
            pulse = request(0, "heartbeat")
            require(pulse.get("status") == "heartbeat", "Heartbeat failed")
            time.sleep(0.55)
        require(request(7, "status").get("status") == "ready", "Heartbeats lost session")
        checks.append("heartbeat_keeps_session")
        time.sleep(1.8)
        require(request(8, "status").get("error") == "stale_session",
                "Watchdog did not invalidate abandoned session")
        checks.append("watchdog_invalidates_session")
        renewed = exchange(device, {"v": 1, "id": 9, "op": "hello"}, 9)
        require(renewed.get("status") == "hello" and renewed.get("session") != session,
                "New handshake did not create a fresh session")
        session = renewed["session"]
        require(request(10, "stop").get("status") == "stopped", "New session unusable")
        checks.append("new_session_recovers")
        return {"port": port, "chip": hello["chip"], "firmware": hello.get("firmware"),
                "ble_name": hello["ble_name"], "ble_connected": stopped["ble_connected"],
                "protocol_checks": checks}
    finally:
        device.close()


async def host_checks(port: str) -> list[str]:
    checks: list[str] = []
    for cycle in range(2):
        bridge = SerialBridge(port)
        try:
            await bridge.open()
            if cycle == 0:
                await asyncio.sleep(2.2)
            require(bridge.connected, "Production host connection expired")
            require((await bridge.request("status"))["status"] == "ready",
                    "Production host status failed")
            result = await bridge.stop()
            require(result["cancelled"] is True, "Production host stop failed")
            if not bridge.ble_connected:
                require(result["release"] == "board_state_cleared_phone_disconnected",
                        "Production host overstated phone release")
            checks.append("host_heartbeat_status_stop" if cycle == 0 else "host_reopen")
        finally:
            await bridge.close()
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Explicit board serial port, e.g. COM5")
    args = parser.parse_args()
    try:
        report = protocol_checks(args.port)
        report["host_checks"] = asyncio.run(host_checks(args.port))
        report["hid_actions_sent"] = False
        report["phone_input_verified"] = False
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, OSError, serial.SerialException) as exc:
        print(json.dumps({"port": args.port, "passed": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
