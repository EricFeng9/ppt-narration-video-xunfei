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
