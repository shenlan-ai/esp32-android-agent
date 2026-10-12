from __future__ import annotations

import argparse
import logging

import uvicorn

from .app import create_app
from .config import RuntimeSettings
from .errors import AgentError


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Android vision agent")
    parser.add_argument(
        "--host", help="Default: 127.0.0.1; remote binding requires an access token"
    )
    parser.add_argument("--port", type=int, help="Default: 8890")
    parser.add_argument("--adb", help="Path to adb executable")
    parser.add_argument("--usb-port", type=int, help="Board TCP port; default 8891, enabled after provisioning")
    args = parser.parse_args()
    try:
        settings = RuntimeSettings.from_env()
        if args.host:
            settings.host = args.host
        if args.port:
            settings.port = args.port
        if args.adb:
            settings.adb_path = args.adb
        if args.usb_port:
            settings.usb_port = args.usb_port
        settings = RuntimeSettings.model_validate(settings.model_dump())
        settings.check_access()
    except (AgentError, ValueError) as exc:
        parser.error(str(exc))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
