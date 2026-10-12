"""PyInstaller entry point; source users keep python -m android_agent."""
import sys

from android_agent.__main__ import main

if __name__ == "__main__":
    # PyInstaller's isolated Python ignores PYTHONUTF8. Keep diagnostic pipes
    # predictable even when Windows uses a legacy Chinese system code page.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
