# Validation

2026-10-14, Windows, repository publication preflight.

- Read AGENTS.md, DEVELOPMENT.md, project-governance and mcp-device-tools specifications, pending diff and related new archives. `openspec list --specs` showed 18 formal specifications; initially no active changes.
- `openspec validate correct-accelerated-demo-description --strict --no-interactive` passed before changing README.md. Documentation only, no specification delta.
- Replaced one stale English phrase with the explicit 5× demo description. Did not modify historical archives, media, product code or phone state in this correction.
- `.venv\Scripts\python .runtime-local/demo-speed5-check-docs.py`: passed, 81 local Markdown targets, 5× embeds/captions, unchanged frontend image references, video sizes and SHA256.
- `.venv\Scripts\python -m pytest -q server/tests`: 369 passed, 1 Windows symlink-permission skip, 1 Starlette/AnyIO deprecation warning, 38.21 seconds. This checks the accumulated MCP implementation intended for this publication, not new physical-device acceptance.
- `.venv\Scripts\python -m ruff check --config server/pyproject.toml server scripts tools packaging`: passed.
- `node --test server/tests/console.test.mjs server/tests/geometry.test.mjs server/tests/board-status.test.mjs`: 9 passed. An earlier command named the nonexistent console-state.test.mjs and ran only 5 geometry/status tests; the corrected command above ran all 9.
- `.venv\Scripts\python -m unittest discover -s scripts/tests`: 59 passed, including native shared-firmware tests, 33.232 seconds. The flash_board usage error is an expected negative test; no board was flashed.
- `git diff --check`: passed with existing LF/CRLF conversion warnings only.
- `.venv\Scripts\python scripts/check_changes.py`: passed before final metadata completion; final scope check repeated before commit.
- High-confidence credential/private-key scan of the 56 then-pending text/media file paths passed; ignored local runtime, credentials and machine MCP configuration remain excluded.
- `git fetch origin` succeeded and `git rev-list --left-right --count HEAD...origin/main` returned `0 0`; publication can use a normal fast-forward push without rewriting remote history.
- Pre-archive strict validation: 18 formal specifications plus this change passed; all 45 existing archived changes passed. Archive and final formal/archive/scope checks run before commit, with results in the session tool output.

This correction adds no compatibility or performance claims. No new phone actions, firmware build/flash, portable build, paid model calls or remote CI execution were performed as part of preflight. Python 3.10 results remain the earlier recorded evidence; this preflight reran the current local Python environment only.
