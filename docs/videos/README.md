# MCP demos

Both public videos play at **5× speed**. Playback duration is not real task execution time. The complete recorded content is uniformly accelerated, with no additional time ranges cut.

## Notes drawing demo

https://github.com/user-attachments/assets/a9684549-7658-43ef-bc77-612e874a5bbe

[Download the 5× MP4](mcp-notes-smiley.mp4) · [Source recording acceptance](../acceptance/2026-10-14-mcp-smiley-recording.md)

Recorded on 2026-10-14 with Redmi Note14 5G (24094RAD4C), Android 15 / API 35, classic ESP32-D0WD-V3 / 4 MB and BLE firmware 0.1.4. Codex used native `android_agent` MCP tools and ESP32 BLE for all phone input. ADB supplied observations and screenrecord, without injecting input.

The clip covers a blank Xiaomi Notes canvas, three `circle` inputs, one continuous nine-point `path`, and saving. Note creation and reopening for persistence verification happened outside the recording to avoid publishing other notes. This recorded replay is separate from the earlier new-session acceptance.

| Property | Value |
|---|---|
| Playback duration | 19.03 seconds at 5× speed |
| Original recording | 95.17 seconds |
| Video | MP4, H.264 High, yuv420p, 720×1512, 30 fps |
| Audio | None |
| File size | 141,307 bytes (about 138 KiB) |
| SHA256 | `47930e3d64500a63ed6520af141c8296bb5ab93793fcfab837039dad643aab75` |
| Source MP4 SHA256 | `9bef42a8e68526bae6994e68e63ffb929ae49323b460cd120f46909c64d787d3` |

## Alarm demo

https://github.com/user-attachments/assets/d2361069-e9da-40d0-9476-7b103fe9ed76

[Download the 5× MP4](mcp-alarm-demo.mp4) · [Source recording acceptance](../acceptance/2026-10-14-mcp-alarm-recording.md)

The same Codex + MCP / Android 15 / ESP32 BLE setup created a new 07:30 one-time alarm and verified it enabled. Existing disabled 06:00, 07:00 and 08:00 alarms stayed unchanged. ADB provided recording and read-only observations.

The original 241.90-second video joins two real recordings: 175.47 seconds up to selecting 07:30, then 66.43 seconds reopening the new alarm, checking its time/repeat setting, saving unchanged values and confirming the enabled list. Android's time limit ended the first segment before initial saving; that save was verified through MCP outside the clip. About 24 minutes between segments are unrecorded. The accelerated version retains this join at about **35.09 seconds**. Actual ringing was not tested.

| Property | Value |
|---|---|
| Playback duration | 48.40 seconds at 5× speed |
| Original recordings | 241.90 seconds total; two segments |
| Video | MP4, H.264 High, yuv420p, 720×1512, 30 fps |
| Audio | None |
| File size | 547,378 bytes (about 535 KiB) |
| SHA256 | `9d8bbabae52c482bad0277cd1f615e4c6e383543900baca9abc4511d0c97f7ca` |
| Source MP4 SHA256 | `4756c688de36f9d5e23fa8cecd5514ac162e03ce9d70c0c0fde4dfa44eeabc7a` |

## Processing and verification

The native recordings were 720×1600. The previous original-speed MP4s cropped only the top 64 and bottom 24 pixels, removed audio/Android metadata and used H.264/yuv420p with fast-start. Those source MP4s are preserved locally in ignored `.runtime-local/`.

The new files derive from those SHA256-verified sources using `setpts=(PTS-STARTPTS)/5,fps=30`, libx264 CRF 23, yuv420p, no audio, removed metadata and fast-start. Only timing/frame sampling and encoding changed. The crop, actual phone contents, stroke order and alarm segment join remain intact. There are no generated frames, overlays or new cuts.

Both files passed full decode, codec/dimension/audio checks, source-duration/5 comparison (within one output frame) and `moov` before `mdat` checks. First/middle/end frames show the drawing progression and saved smiley, and the alarm time selection and enabled final list. GitHub embeds and repository download files use these same 5× outputs.

These are evidence for the listed setup and tasks, not performance or success-rate benchmarks. [Image provenance](../images/README.md) records the frontend screenshot separately. Raw recordings, source-speed copies and private logs remain ignored.
