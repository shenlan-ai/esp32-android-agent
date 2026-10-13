# Validation — refresh-english-readme

Date: 2026-10-13, Windows/PowerShell, existing Python venv. Documentation and source-manifest update only; service, firmware and control behavior unchanged.

## Documentation

- README.md is the full default English entry. README.zh-CN.md contains matching Chinese setup, console/MCP use and evidence boundaries. README.en.md preserves the previous entry URL as a pointer.
- New console image is explicitly identified as offline DEMO. Real phone cases and older UI image retain provenance and failure/manual-intervention limits. MCP reports the real Codex input-focus failure and guided successful second attempt; no general model accuracy or universal device support claim.
- Updated CONTRIBUTING.md, docs/DEVELOPMENT.md and docs/USAGE.en.md links. Added README.zh-CN.md to the existing portable source allowlist, keeping confidential/generated paths excluded.

## Executed checks

- `openspec list --specs` / `openspec list`: read governance, product, MCP and console formal requirements; 18 specs, no active change before this one.
- `openspec validate refresh-english-readme --strict --no-interactive`: PASS before implementation; skip_specs explicitly declares no product requirement changes.
- Inline Python link/anchor/language/source-manifest check: 101 local Markdown links/anchors PASS across current changed/new Markdown. English default and reciprocal language entries verified. All three README files allowed in portable source manifest; settings.local.json excluded.
- Inline byte-pattern scan: 59 changed/new files checked, no API-key-shaped strings, GitHub tokens or private-key headers found. Prints paths/categories only if a match exists, never values; image binaries excluded from text scanning. File scope separately reviewed for personal configuration, local screenshots and flash backups; none included.
- `.venv/Scripts/python -m android_agent --help` and `... -m android_agent.mcp --help`: PASS; documented browser, port, ADB and MCP URL options exist. `codex mcp add --help`: confirms stdio registration syntax. No registration command executed and no user Codex setting changed by documentation validation.
- `.venv/Scripts/python -m unittest discover -s scripts/tests`: 59 PASS, 33.255s; includes portable/release-source policy and real shared C++ checks. Expected firmware overwrite-consent rejection appears in a negative test; no board flashed.
- `node --test server/tests/console.test.mjs server/tests/geometry.test.mjs server/tests/board-status.test.mjs`: 9 PASS, 0 failed.
- `.venv/Scripts/python -m ruff check --config server/pyproject.toml server scripts tools packaging`: PASS.
- `.venv/Scripts/python scripts/check_workflows.py`: PASS.
- `git -c core.safecrlf=false diff --check`: PASS.
- `python scripts/check_changes.py`: PASS, includes prior MCP/UI work covered by their newly created archives.
- `openspec validate --all --strict --no-interactive`: before archive, 19/19 PASS (18 specs + this change). `openspec validate --archived --no-interactive`: before archive, 39/39 PASS. Final post-archive checks and staged diff/scope check run before commit.

## Reused current implementation evidence

- MCP archive: Python3.12 and 3.10 each 347 passed, one Windows symlink skip and one dependency warning; 48 MCP tests and actual Codex/Redmi Note14/Android15/BLE0.1.4 trials. See add-mcp-device-tools validation and docs/acceptance/2026-10-13-codex-mcp.md.
- Latest UI archive: Python3.12 347 passed/one same skip/one warning, 9 frontend tests, three consecutive final offline browser passes, responsive/zoom/stop/drafts/persistence/failure checks and screenshot review. See redesign-local-console validation.
- Backend/firmware code was not changed in this README update, so those whole suites were not repeated. No new physical input, paid model call, image-generation call, firmware build/flash, portable rebuild or hardware acceptance was performed.

## Publication preparation

Origin is https://github.com/shenlan-ai/esp32-android-agent.git, public repository, default branch main. `git fetch origin` succeeded; `git rev-list --left-right --count HEAD...origin/main` returned 0/0 before edits. User explicitly authorized committing and pushing all current completed MCP/UI/documentation modifications. Use normal fast-forward push, no force. Archive this documentation change after development checks; stage reviewed source/metadata/design assets only and verify staged scope/diff before commit. The resulting commit SHA, remote agreement and actual CI state are checked and reported at delivery rather than writing a self-referential SHA into this commit.
