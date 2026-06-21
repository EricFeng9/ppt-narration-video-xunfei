---
name: ppt-narration-video-xunfei
description: Generate narrated presentation videos from PDF or PPTX files using Xunfei TTS, including AI-written or user-provided narration, per-slide subtitles, timeline JSON, and MP4 exports with and without subtitle tracks. Use when the user asks to turn a PPT/PDF deck into a narrated explanation, report, lecture, or presentation video with Chinese voiceover.
---

# PPT Narration Video With Xunfei

Use this skill to create a complete narrated video from a PDF/PPTX deck.

## Core Workflow

1. Inspect the input file.
   - PDF: render each page directly.
   - PPTX: convert to PDF first with LibreOffice if available, then render.
   - Extract per-page text for script generation.
2. Decide the script path.
   - If the user provides a script, align it to slide/page count.
   - If no script is provided, generate a per-page narration draft and ask the user to confirm or revise before creating audio.
   - If script page count does not match slide/page count, stop and ask for clarification.
3. Check Xunfei credentials.
   - Preferred secret file: `~/.codex/secrets/ppt-narration-video-xunfei.json`
   - If missing, ask the user for `appid`, `apikey`, `apisecret`, and default `voice`.
   - If the user does not know the voice value, guide them to Xunfei console > app > 语音合成 > 在线语音合成 > 发音人授权管理, then copy `参数（vcn/voice_name）`.
   - Save secrets only with `scripts/setup_secret.py`; never write credentials into project files, outputs, logs, subtitles, timelines, or final replies.
4. Check runtime.
   - Use the `fjm` conda Python when no Python is specified.
   - Required Python packages: `fitz`/PyMuPDF, `PIL`, `websocket-client`, `imageio-ffmpeg`.
   - The scripts should expose missing dependency errors directly.
5. Generate assets.
   - Render slides to 1920x1080 PNG by default.
   - Use Xunfei WebSocket TTS to generate one WAV per page.
   - Compose one MP4 segment per page.
   - Generate SRT subtitles and timeline JSON.
6. Export final deliverables.
   - MP4 without subtitle track.
   - MP4 with soft subtitle track.
   - SRT subtitles.
   - Markdown script.
   - Timeline JSON.
7. Verify.
   - Check duration, resolution, video stream, audio stream, subtitle stream.
   - Extract representative frames for visual QA when possible.

## User Confirmation Rule

When no narration script is supplied, generate the per-page script first and ask the user to confirm it. Do not call TTS before the user confirms or supplies a revised script.

## Secret Handling

Use:

```bash
python scripts/setup_secret.py --appid APPID --apikey APIKEY --apisecret APISECRET --voice x4_lingfeizhe_zl
```

The file is saved to:

```text
~/.codex/secrets/ppt-narration-video-xunfei.json
```

The script sets file permission to `0600`.

If the user pasted credentials or sent a screenshot containing credentials, remind them to rotate keys after the task.

## Voice Guidance

The Xunfei voice parameter is `vcn` or `voice_name`. The script option `--voice` must use that exact value.

When users need help choosing or configuring a voice, instruct them:

1. Open Xunfei Open Platform console.
2. Enter the target app.
3. Go to `语音合成`.
4. Open `在线语音合成`.
5. Find `发音人授权管理`.
6. Choose `基础发音人` or `特色发音人`.
7. Expand the chosen voice row.
8. Copy `参数（vcn/voice_name）`, such as `x4_lingfeizhe_zl`.

Only use voices whose status is `已开通`.

## Main Command

After the script is confirmed and credentials exist:

```bash
python scripts/make_video.py \
  --input /path/to/deck.pdf \
  --script /path/to/script.md \
  --output-dir /path/to/outputs \
  --voice x4_lingfeizhe_zl
```

For PPTX input, the script attempts PDF conversion before rendering:

```bash
python scripts/make_video.py \
  --input /path/to/deck.pptx \
  --script /path/to/script.md \
  --output-dir /path/to/outputs
```

## Script Format

Preferred:

```markdown
## 第1页：封面

第一页讲解词。

## 第2页：目录

第二页讲解词。
```

Also accept plain text split by page labels such as `第1页：`.

## Defaults

- Aspect ratio: 16:9
- Resolution: 1920x1080
- FPS: 30
- Voice: secret file `default_voice`, otherwise `x4_lingfeizhe_zl`
- Output prefix: input filename stem plus voice name

## Failure Policy

- Environment issue: install or use existing local runtime when safe; if blocked, report exact missing command/package.
- Xunfei connection issue: retry per page up to 5 times; preserve successful audio and resume.
- API authorization issue: stop and report the exact Xunfei response code/message.
- Slide/script mismatch: stop and ask the user to correct the script or approve generated alignment.
