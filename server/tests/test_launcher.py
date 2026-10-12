from unittest.mock import patch

import pytest
import uvicorn

from android_agent.config import RuntimeSettings
from android_agent.launcher import (
    LauncherServer,
    bind_socket,
    browser_url,
    diagnostic_json,
    resolve_adb,
)


def test_adb_precedence_and_source_is_not_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("ADB_PATH", raising=False)
    (tmp_path / "platform-tools").mkdir()
    adjacent = tmp_path / "platform-tools/adb.exe"
    adjacent.write_bytes(b"test")
    assert resolve_adb(None, tmp_path) == str(adjacent)
    monkeypatch.setenv("ADB_PATH", "chosen-by-environment")
    assert resolve_adb(None, tmp_path) == "chosen-by-environment"
    assert resolve_adb("explicit", tmp_path) == "explicit"
    monkeypatch.delenv("ADB_PATH")
    with patch("android_agent.launcher.portable_root", return_value=None):
        monkeypatch.chdir(tmp_path)
        assert resolve_adb(None) == "adb"


def test_bound_socket_cannot_be_replaced():
    with bind_socket("127.0.0.1", 0) as owned:
        with pytest.raises(OSError):
            bind_socket("127.0.0.1", owned.getsockname()[1])
        assert owned.fileno() >= 0


def test_diagnostics_do_not_serialize_secrets(tmp_path):
    settings = RuntimeSettings(data_dir=tmp_path, access_token="secret-for-test", adb_path="missing")
    report = diagnostic_json(settings)
    assert '"adb_available": false' in report
    assert "secret-for-test" not in report
    assert browser_url(settings) == "http://127.0.0.1:8890/"
    assert browser_url(RuntimeSettings(host="::1")) == "http://[::1]:8890/"
    assert browser_url(RuntimeSettings(host="0.0.0.0")) is None


@pytest.mark.asyncio
async def test_failed_startup_does_not_open_browser():
    server = LauncherServer(uvicorn.Config(lambda: None), "http://127.0.0.1:8890/")
    with patch.object(uvicorn.Server, "startup"), patch("webbrowser.open") as opened:
        await server.startup()
        opened.assert_not_called()


@pytest.mark.asyncio
async def test_open_browser_only_after_successful_startup():
    server = LauncherServer(uvicorn.Config(lambda: None), "http://127.0.0.1:8890/")

    async def startup(sockets=None):
        server.started = True

    with patch.object(uvicorn.Server, "startup", side_effect=startup), patch("webbrowser.open") as opened:
        await server.startup()
        opened.assert_called_once_with("http://127.0.0.1:8890/")
