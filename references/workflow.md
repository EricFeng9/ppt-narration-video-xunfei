# Workflow Notes

Use this reference when implementing or debugging a presentation video run.

## Script Confirmation

If no script exists, Codex should generate a per-page `script.md` from extracted slide text and ask the user to approve it before TTS.

Use this shape:

```markdown
## 第1页：封面

讲稿内容。
```

## Xunfei Voice

The Xunfei WebAPI voice parameter is `vcn`.

To guide a user:

1. Open Xunfei Open Platform console.
2. Enter the app.
3. Open `语音合成` > `在线语音合成`.
4. Locate `发音人授权管理`.
5. Select `基础发音人` or `特色发音人`.
6. Expand a voice row and copy `参数（vcn/voice_name）`.
7. Confirm status is `已开通`.

Examples:

- `x4_lingfeizhe_zl`
- `x4_lingbosong`

Use the user's selected voice exactly.

## Deliverable Naming

Recommended output files:

- `{prefix}.mp4`
- `{prefix}_with_subtitles.mp4`
- `{prefix}.srt`
- `{prefix}_script.md`
- `{prefix}_timeline.json`
- `{prefix}_verify.txt`
