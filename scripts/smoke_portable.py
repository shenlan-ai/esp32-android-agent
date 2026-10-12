"""Verify an extracted portable application with a real, device-free subprocess."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from collect_firmware import sha256


def verify_inventory(folder: Path) -> None:
    inventory = json.loads((folder / "checksums.json").read_text(encoding="utf-8"))
    for name, info in inventory.items():
        path = folder / name
        if (Path(name).is_absolute() or not path.resolve().is_relative_to(folder.resolve())
                or path.is_symlink() or not path.is_file()):
            raise ValueError(f"Unsafe or missing packaged path: {name}")
        if path.stat().st_size != info["size"] or sha256(path) != info["sha256"]:
            raise ValueError(f"Corrupt packaged file: {name}")
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    if actual != {*inventory, "checksums.json"}:
        raise ValueError("Unexpected extra files in the distribution; validate before adding ADB or data")


def smoke(executable: Path) -> dict:
    executable = executable.resolve()
    verify_inventory(executable.parent)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("ANDROID_AGENT_", "ADB_", "LLM_", "ACTOR_", "PLANNER_", "PYTHON"))}
    environment["PATH"] = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32")
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONUTF8"] = "1"
    tool = executable.parent / "tools/firmware-tool/firmware-tool.exe"
    diagnosis = subprocess.run([str(tool), "diagnose"], env=environment,
                               cwd=executable.parent, capture_output=True, text=True,
                               encoding="utf-8", timeout=30, check=True)
    firmware_tool = json.loads(diagnosis.stdout)
    if (firmware_tool.get("protocol") != "android-agent-firmware-v1" or firmware_tool.get("ok") is not True
            or firmware_tool.get("esptool") != "5.3.0" or firmware_tool.get("device_used") is not False):
        raise ValueError("Isolated firmware tool diagnosis failed")
    with tempfile.TemporaryDirectory(prefix="android-agent-smoke-") as temporary:
        data = Path(temporary) / "用户 data"
        missing = Path(temporary) / "missing-adb.exe"
        with socket.socket() as available:
            available.bind(("127.0.0.1", 0))
            port = available.getsockname()[1]
        args = [str(executable), "--no-browser", "--port", str(port), "--data-dir", str(data), "--adb", str(missing)]
        diagnosis = subprocess.run([*args, "--diagnose"], env=environment, cwd=temporary,
                                   capture_output=True, text=True, encoding="utf-8", timeout=30, check=True)
        report = json.loads(diagnosis.stdout)
        if not report["portable"] or report["adb_available"] or Path(report["data_dir"]) != data:
            raise ValueError("Portable diagnostics did not use the isolated missing-ADB environment")
        # HTTP access uses no proxy or outside network.
        http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        url = f"http://127.0.0.1:{port}"
        with (Path(temporary) / "process.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(args, cwd=temporary, env=environment, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 30
                while True:
                    if process.poll() is not None:
                        raise ValueError(f"Portable server exited: {(Path(temporary) / 'process.log').read_text()}")
                    try:
                        with http.open(url + "/api/status", timeout=1) as response:
                            status = json.load(response)
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise ValueError("Portable application did not become ready within 30 seconds") from None
                        time.sleep(0.1)
                if status["adb_available"]:
                    raise ValueError("Smoke accidentally found a real ADB")
                for path, expected in (("/", b"<!doctype html>"), ("/static/app.js", b"import"),
                                       ("/static/style.css", b"{"), ("/static/i18n.js", b"export"),
                                       ("/static/firmware.js", b"createFirmwareSetup")):
                    with http.open(url + path, timeout=5) as response:
                        if response.status != 200 or expected not in response.read():
                            raise ValueError(f"Missing portable web content: {path}")
                with http.open(url + "/api/firmware", timeout=5) as response:
                    fw = json.load(response)
                if (not fw["tool_available"] or not fw["catalog"]["available"] or fw["busy"]
                        or {item["profile"] for item in fw["catalog"]["profiles"]} != {
                            "esp32dev", "esp32_s3_devkitc", "xiao_esp32s3", "esp32_s3_zero"}):
                    raise ValueError("Portable firmware catalog or tool unavailable")
                try:
                    http.open(url + "/api/devices", timeout=5)
                    raise ValueError("Missing ADB should produce an actionable device error")
                except urllib.error.HTTPError as error:
                    if error.code != 409 or b"ADB" not in error.read():
                        raise ValueError("Unexpected missing-ADB response") from error
                conflict = subprocess.run(args, check=False, env=environment, cwd=temporary, capture_output=True,
                                          text=True, encoding="utf-8", timeout=30)
                if conflict.returncode != 1 or "Cannot listen" not in conflict.stderr:
                    raise ValueError(f"Port conflict did not fail clearly: {conflict.stderr}")
                with http.open(url + "/api/status", timeout=5) as response:
                    if json.load(response)["version"] != report["version"]:
                        raise ValueError("Conflicting launcher changed the original service")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        return {"portable": True, "version": report["version"], "inventory": "passed",
                "diagnostics": "passed", "static_and_api": "passed", "missing_adb": "passed",
                "port_conflict": "passed", "system_python_and_adb": "excluded",
                "firmware_tool_diagnose": "passed", "firmware_catalog": "four profiles",
                "phone_or_board_used": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    print(json.dumps(smoke(args.executable), indent=2))


if __name__ == "__main__":
    main()
