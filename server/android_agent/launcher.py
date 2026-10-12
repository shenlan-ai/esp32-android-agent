"""Application startup shared by source and the Windows portable entry point."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import shutil
import socket
import sys
import webbrowser
from pathlib import Path

import uvicorn

from . import __version__
from .config import RuntimeSettings

ADB_DOWNLOAD = "https://developer.android.com/tools/releases/platform-tools"


def portable_root() -> Path | None:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None


def resolve_adb(explicit: str | None, root: Path | None = None) -> str:
    if explicit:
        return explicit
    if os.environ.get("ADB_PATH"):
        return os.environ["ADB_PATH"]
    root = root if root is not None else portable_root()
    if root and (root / "platform-tools/adb.exe").is_file():
        return str(root / "platform-tools/adb.exe")
    return "adb"


def diagnostics(settings: RuntimeSettings) -> dict:
    return {
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "portable": portable_root() is not None,
        "data_dir": str(settings.data_dir.resolve()),
        "host": settings.host,
        "port": settings.port,
        "adb": settings.adb_path,
        "adb_available": bool(shutil.which(settings.adb_path)),
        "adb_download": ADB_DOWNLOAD,
    }


def diagnostic_json(settings: RuntimeSettings) -> str:
    # Do not serialize settings: it also contains access tokens.
    return json.dumps(diagnostics(settings), ensure_ascii=False, indent=2)


def bind_socket(host: str, port: int) -> socket.socket:
    # Keep this socket through startup; a separate availability probe would race.
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    family, socktype, protocol, _, address = addresses[0]
    sock = socket.socket(family, socktype, protocol)
    try:
        if os.name == "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(address)
        sock.listen(128)
        sock.setblocking(False)
        return sock
    except BaseException:
        sock.close()
        raise


def browser_url(settings: RuntimeSettings) -> str | None:
    if not settings.local_only:
        return None
    host = "[::1]" if settings.host == "::1" else settings.host
    return f"http://{host}:{settings.port}/"


class LauncherServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, url: str | None):
        super().__init__(config)
        self.browser_url = url

    async def startup(self, sockets=None) -> None:
        await super().startup(sockets=sockets)
        if self.started and self.browser_url:
            try:
                await asyncio.to_thread(webbrowser.open, self.browser_url)
            except Exception:
                logging.getLogger(__name__).warning("Open the displayed URL in your browser")


def serve(app, settings: RuntimeSettings, open_browser: bool) -> None:
    with bind_socket(settings.host, settings.port) as sock:
        config = uvicorn.Config(app, host=settings.host, port=settings.port, log_level="info",
                                loop="asyncio", http="h11", ws="none")
        url = browser_url(settings)
        logging.getLogger(__name__).info("Data directory: %s", settings.data_dir.resolve())
        if url:
            logging.getLogger(__name__).info("Workbench: %s", url)
        LauncherServer(config, url if open_browser else None).run(sockets=[sock])
