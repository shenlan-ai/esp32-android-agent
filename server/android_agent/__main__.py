from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .app import create_app
from .config import RuntimeSettings
from .errors import AgentError
from .launcher import diagnostic_json, portable_root, resolve_adb, serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Android vision agent")
    parser.add_argument(
        "--host", help="Default: 127.0.0.1; remote binding requires an access token"
    )
    parser.add_argument("--port", type=int, help="Default: 8890")
    parser.add_argument("--adb", help="Path to adb executable")
    parser.add_argument("--data-dir", type=Path, help="User data directory (outside the program)")
    parser.add_argument("--diagnose", action="store_true", help="Print diagnostics and exit")
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument("--open-browser", dest="browser", action="store_true")
    browser.add_argument("--no-browser", dest="browser", action="store_false")
    parser.set_defaults(browser=None)
    parser.add_argument("--usb-port", type=int, help="Board TCP port; default 8891, enabled after provisioning")
    args = parser.parse_args()
    try:
        settings = RuntimeSettings.from_env()
        if args.host:
            settings.host = args.host
        if args.port is not None:
            settings.port = args.port
        settings.adb_path = resolve_adb(args.adb)
        if args.data_dir is not None:
            settings.data_dir = args.data_dir
        if args.usb_port is not None:
            settings.usb_port = args.usb_port
        settings = RuntimeSettings.model_validate(settings.model_dump())
        settings.check_access()
    except (AgentError, ValueError) as exc:
        parser.error(str(exc))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.diagnose:
        print(diagnostic_json(settings))
        return
    try:
        serve(create_app(settings), settings,
              args.browser if args.browser is not None else portable_root() is not None)
    except OSError:
        parser.exit(1, f"Cannot listen on {settings.host}:{settings.port}. "
                    "The port may be occupied; close that program or use --port.\n")


if __name__ == "__main__":
    main()
