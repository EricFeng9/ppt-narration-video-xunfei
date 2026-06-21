# ppt-narration-video-xunfei

<p>
  <a href="./README.md">中文</a>
  |
  <a href="./README.en.md">English</a>
</p>

A Codex skill for turning a PDF or PPTX presentation into a narrated Chinese video with Xunfei TTS voiceover, subtitles, timeline metadata, and MP4 exports.

## What It Does

This skill handles the full presentation-to-video workflow:

1. Read a PDF or PPTX deck.
2. Render each slide/page to a 1920x1080 image.
3. Use a confirmed per-page narration script.
4. Generate one Xunfei TTS audio file per page.
5. Create SRT subtitles and a timeline JSON.
6. Export two videos:
   - MP4 without subtitle track
   - MP4 with soft subtitle track
7. Verify the final video stream, audio stream, subtitle stream, and duration.

If no narration script is provided, Codex should first generate a per-page script draft from the slide content and ask the user to confirm or revise it before calling TTS.

## Skill Structure

```text
ppt-narration-video-xunfei/
├── SKILL.md
├── README.md
├── README.en.md
├── agents/
│   └── openai.yaml
├── references/
│   └── workflow.md
└── scripts/
    ├── setup_secret.py
    └── make_video.py
```

## Install

Copy this folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R ppt-narration-video-xunfei ~/.codex/skills/
```

Then start a new Codex session or reload skills if your Codex surface supports it.

## Requirements

Use the `fjm` conda environment by default unless another Python environment is explicitly requested.

Required Python packages:

```bash
pip install pymupdf pillow websocket-client imageio-ffmpeg
```

For PPTX input, install LibreOffice so the script can convert PPTX to PDF:

```bash
brew install --cask libreoffice
```

PDF input does not require LibreOffice.

## Configure Xunfei API

Save credentials locally with:

```bash
python scripts/setup_secret.py \
  --appid "YOUR_APPID" \
  --apikey "YOUR_APIKEY" \
  --apisecret "YOUR_APISECRET" \
  --voice "x4_lingfeizhe_zl"
```

The script writes:

```text
~/.codex/secrets/ppt-narration-video-xunfei.json
```

File permission is set to `0600`.

Do not commit this secret file. Do not place API keys in project folders, outputs, subtitles, timelines, or README files.

## Configure Voice

The Xunfei voice parameter is called `vcn` or `voice_name`. The skill's `--voice` option is exactly this value.

How to find the voice parameter in the Xunfei console:

1. Open the Xunfei Open Platform console.
2. Enter your application.
3. Select `语音合成`.
4. Open `在线语音合成`.
5. In `发音人授权管理`, choose `基础发音人` or `特色发音人`.
6. Find the voice you want to use.
7. Expand the voice row and copy `参数（vcn/voice_name）`.

Examples:

```text
Lingfeizhe: x4_lingfeizhe_zl
Lingbosong: x4_lingbosong
```

Save it as the default voice:

```bash
python scripts/setup_secret.py \
  --appid "YOUR_APPID" \
  --apikey "YOUR_APIKEY" \
  --apisecret "YOUR_APISECRET" \
  --voice "x4_lingfeizhe_zl"
```

Or override it for one video run:

```bash
python scripts/make_video.py \
  --input /path/to/deck.pdf \
  --script /path/to/script.md \
  --output-dir /path/to/outputs \
  --voice x4_lingfeizhe_zl
```

The voice must be marked as `已开通` in the console. If it is not enabled, API authentication may succeed but synthesis will fail.

## Script Format

Use one section per page:

```markdown
## 第1页：封面

各位领导好，下面汇报本项目方案。

## 第2页：目录

本次汇报分为前期分析、目标定位、方案设计和专项设计四个部分。
```

The script page count must match the slide/page count.

## Generate Video

PDF example:

```bash
python scripts/make_video.py \
  --input /path/to/deck.pdf \
  --script /path/to/script.md \
  --output-dir /path/to/outputs \
  --voice x4_lingfeizhe_zl
```

PPTX example:

```bash
python scripts/make_video.py \
  --input /path/to/deck.pptx \
  --script /path/to/script.md \
  --output-dir /path/to/outputs \
  --voice x4_lingfeizhe_zl
```

Optional controls:

```bash
--speed 50
--volume 60
--pitch 50
--prefix custom_output_name
--work-dir /path/to/work
```

## Outputs

The script creates:

```text
{prefix}.mp4
{prefix}_with_subtitles.mp4
{prefix}.srt
{prefix}_script.md
{prefix}_timeline.json
{prefix}_verify.txt
```

## Security Notes

- Store Xunfei credentials only in `~/.codex/secrets/ppt-narration-video-xunfei.json`.
- Keep secret file permission at `0600`.
- If credentials were pasted into chat or exposed in screenshots, rotate them after use.
- The skill scripts do not print API secrets.

## Typical Codex Prompt

```text
Use $ppt-narration-video-xunfei to turn this PDF into a narrated presentation video. If no script is provided, draft the per-page narration first and ask me to confirm before generating TTS.
```
