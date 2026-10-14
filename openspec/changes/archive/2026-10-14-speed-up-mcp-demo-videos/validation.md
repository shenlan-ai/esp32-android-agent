# Validation — 2026-10-14

This is a media/documentation change. The proposal, design, tasks and file scope were written and strictly validated before implementation. The existing frontend screenshot is unchanged.

## Encoding and media checks

Command: `.venv\Scripts\python .runtime-local/demo-speed5.py` — passed. Source copies are retained in ignored local storage and their SHA256 values were checked before encoding; reruns use these original sources instead of accelerating the accelerated files again.

Both videos use `setpts=(PTS-STARTPTS)/5,fps=30`, H.264 High, yuv420p, 720×1512, no audio, and fast-start. Complete decoding succeeded, MP4 `moov` precedes `mdat`, and duration agrees with source duration divided by five within one output frame. First/middle/final contact-sheet frames were visually inspected: the smiley and enabled 07:30 alarm remain visible at the end.

| File | Original duration | Current duration | Bytes | Current SHA256 |
| --- | --- | --- | --- | --- |
| mcp-notes-smiley.mp4 | 95.166667 s | 19.033333 s | 141307 | 47930e3d64500a63ed6520af141c8296bb5ab93793fcfab837039dad643aab75 |
| mcp-alarm-demo.mp4 | 241.90 s | 48.40 s | 547378 | 9d8bbabae52c482bad0277cd1f615e4c6e383543900baca9abc4511d0c97f7ca |

Verified original SHA256: smiley `9bef42a8e68526bae6994e68e63ffb929ae49323b460cd120f46909c64d787d3`; alarm `4756c688de36f9d5e23fa8cecd5514ac162e03ce9d70c0c0fde4dfa44eeabc7a`.

## README playback and documentation

Uploaded the accelerated files through a GitHub issue draft; no issue or comment was published. GitHub Markdown preview rendered native players with controls, `readyState=4`, no playback errors, and durations 19.033333 and 48.4 seconds. Both players were started successfully and their playback time advanced. Local proof: `.runtime-local/demo-speed5-playback-proof.jpg`.

- Smiley attachment: https://github.com/user-attachments/assets/a9684549-7658-43ef-bc77-612e874a5bbe
- Alarm attachment: https://github.com/user-attachments/assets/d2361069-e9da-40d0-9476-7b103fe9ed76

Updated English/Chinese README embeds, captions and download sizes; media documentation and acceptance reports distinguish current accelerated outputs from original recording evidence. The alarm's existing two-part recording and unrecorded gap remain disclosed; the join moves to approximately 35.09 seconds. Playback duration does not represent real task execution time.

## Repository checks

- `.venv\Scripts\python .runtime-local/demo-speed5-check-docs.py` — passed: 81 local Markdown targets, new embeds/captions, unchanged frontend image references, file sizes and SHA256.
- `git diff --check` — passed; existing line-ending conversion warnings only.
- `.venv\Scripts\python scripts/check_changes.py` — passed; pre-existing changes remain covered by their own active changes.
- `openspec validate speed-up-mcp-demo-videos --strict --no-interactive` — passed before implementation and after documentation updates.
- Final archival and complete formal/archived specification validation are performed as the closing step.

No product regression or firmware tests were rerun because only video/media documentation changed. No phone actions or new recordings were performed. No commit or push was requested or performed for this change.
