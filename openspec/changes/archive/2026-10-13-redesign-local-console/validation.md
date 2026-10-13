# Validation — redesign-local-console

Date: 2026-10-13. Windows host; Python venv and bundled Playwright/Edge. All browser mutations used loopback port 8906 agent_demo with a verified DEMO banner, fake screen/controller/model and isolated local configuration. No real device action or task-model call was performed for this UI change.

## Installation and design

- Installed globally via skill-installer: oil-ui 0.22.2, source commit aaa66f4c48036da8910752812d5a969fb441b3b6; draw-ui source commit e4e03662144ae94ed1140811d054f2a3b255e3e4. Existing oil-ui backed up locally before updating.
- Applied oil-ui, draw-ui and frontend-design. User-authorized image service https://best-api.huggingclaw.store, model gpt-image-2.5 produced docs/design/console-2026-10-13/design-generated.png, 1536×1024. Opened and visually inspected. Prompt and direction retained alongside it. Credential was supplied only at runtime, not in project files or logs; application model configuration was not changed.
- Two independent screenshot reviews scored 7/10 each. Initial issues were fixed; the second review led to settings-first order under zoom, full-row device identity and narrow-screen subtitle reduction. Final affected images were visually checked by the main agent, without assigning a new independent score. Remaining visual limitation: restrained panel shell is still somewhat generic. No score of 8+ claimed.

## Commands and results

- Before implementation and after scope decisions: `openspec validate redesign-local-console --strict --no-interactive` — PASS.
- `.venv/Scripts/python -m pytest -q server/tests -rs` — 347 passed, 1 skipped, 1 warning, 37.56s. Skip: test_history.py:45 host does not allow symlink creation. Warning: installed Starlette's deprecated anyio BlockingPortal alias. No changed dependency needed.
- `node --test server/tests/console.test.mjs server/tests/geometry.test.mjs server/tests/board-status.test.mjs` — 9 passed, 0 failed. Covers module-bound DOM/i18n contracts, navigation/focus/drafts, real model/task summaries, readiness hints and geometry.
- `node scripts/check_console_ui.mjs http://127.0.0.1:8906 C:/Users/yaolan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules` — final code consecutive run 1 PASS (93312), run 2 PASS (23896), run 3 PASS (52139). Earlier passes preceded review fixes and do not count as final consecutive runs.
- Browser checks: keyboard Enter navigation and focused title; mounted unsaved drafts; settings saved then read after reload; intercepted failed save retains input/view; bilingual labels; BLE/USB/calibration/firmware entries reachable with write gate disabled; task completion/clear/pause/resume; stop from settings and Esc; 1440×900, 1024×768, 390×844, 720×450 without horizontal overflow; stop remains visible after scroll; task-first narrow workspace; readable full-row device selector; screen error title; actual CSS zoom=2 readable settings width and settings-before-preview; reduced-motion disabled animation; no JS errors.
- `.venv/Scripts/python -m ruff check --config server/pyproject.toml server scripts tools packaging` — PASS.
- `git -c core.safecrlf=false diff --check` — PASS.
- `python scripts/check_changes.py` — PASS; preserves separately covered pre-existing MCP work.
- `openspec validate --all --strict --no-interactive` and `openspec validate --archived --no-interactive` — checked before and after archive; successful results recorded in task completion.

## Visual evidence and limits

- oil-ui `shoot.mjs` with desktop/phone, view workspace/devices/settings, evidence and navigation steps — static screenshots have empty issues/lint arrays. Final capture in .runtime-local/console-final/report.json. Tool exits 1 because ffmpeg is absent (two video export failures) and a generic scroll-narrative advisory. This is a device console, not a landing/brand page; no scroll narrative is required. Start/mid/end JPGs remain; full videos were not generated or played. Motion probe detects entry/navigation changes; reviewer assessed still frames only.
- @2x screenshots denote pixel density, not 200% browser zoom. Separate CSS zoom=2 and 720px effective viewport checks are recorded above. Main agent viewed desktop workspace/settings, phone workspace/devices and final zoomed settings images, including changed settings order and device-name width.
- Durable generated draft and fixture screenshots: docs/design/console-2026-10-13/. Screenshots use fake content only. No new production dependency or frontend framework. Production build not applicable to static files.
- No new real-hardware compatibility, firmware or control acceptance is claimed. Existing manual control, geometry and safety gates remain covered by regressions, not by UI screenshot evidence.

## Completion

All implementation and applicable checks completed. `openspec archive redesign-local-console --yes` succeeded and added 3 requirements to the formal console-presentation spec. The archive step was the sole unchecked task at command invocation (6/7); it is marked complete in this newly produced, uncommitted archive after successful execution. Final formal/archived/scope checks pass before delivery; this does not modify a previously committed historical archive.
