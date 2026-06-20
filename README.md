# ppt-narration-video-xunfei

<p>
  <a href="./README.md">中文</a>
  |
  <a href="./README.en.md">English</a>
</p>

基于讯飞语音合成的 Codex Skill：把 PDF 或 PPTX 演示文稿生成带中文配音、字幕、时间轴和 MP4 成品的讲解视频。

## 功能

这套 Skill 覆盖完整的“演示文稿转讲解视频”流程：

1. 读取 PDF 或 PPTX。
2. 将每一页渲染为 1920x1080 图片。
3. 使用已经确认的逐页讲稿。
4. 调用讯飞 TTS，为每一页生成独立音频。
5. 生成 SRT 字幕和时间轴 JSON。
6. 导出两个视频：
   - 无字幕轨 MP4
   - 带软字幕轨 MP4
7. 校验最终视频的视频流、音频流、字幕流和总时长。

如果用户没有提供讲稿，Codex 应先根据页面内容生成逐页讲稿草稿，并让用户确认或修改；确认后再调用 TTS。

## 目录结构

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

## 安装

复制本目录到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R ppt-narration-video-xunfei ~/.codex/skills/
```

然后开启新的 Codex 会话，或在支持重载的 Codex 界面中重新加载 Skills。

## 环境要求

默认使用 `fjm` conda 环境，除非用户明确指定其他 Python 环境。

需要的 Python 包：

```bash
pip install pymupdf pillow websocket-client imageio-ffmpeg
```

如果输入是 PPTX，需要安装 LibreOffice，用于把 PPTX 转成 PDF：

```bash
brew install --cask libreoffice
```

PDF 输入不需要 LibreOffice。

## 配置讯飞 API

用下面命令把讯飞凭证保存到本机私有配置文件：

```bash
python scripts/setup_secret.py \
  --appid "YOUR_APPID" \
  --apikey "YOUR_APIKEY" \
  --apisecret "YOUR_APISECRET" \
  --voice "x4_lingfeizhe_zl"
```

脚本会写入：

```text
~/.codex/secrets/ppt-narration-video-xunfei.json
```

文件权限会设置为 `0600`。

不要提交这个密钥文件。不要把 API Key 写进项目目录、输出目录、字幕、时间轴或 README。

## 讲稿格式

每页一个小节：

```markdown
## 第1页：封面

各位领导好，下面汇报本项目方案。

## 第2页：目录

本次汇报分为前期分析、目标定位、方案设计和专项设计四个部分。
```

讲稿页数必须和演示文稿页数一致。

## 生成视频

PDF 示例：

```bash
python scripts/make_video.py \
  --input /path/to/deck.pdf \
  --script /path/to/script.md \
  --output-dir /path/to/outputs \
  --voice x4_lingfeizhe_zl
```

PPTX 示例：

```bash
python scripts/make_video.py \
  --input /path/to/deck.pptx \
  --script /path/to/script.md \
  --output-dir /path/to/outputs \
  --voice x4_lingfeizhe_zl
```

可选参数：

```bash
--speed 50
--volume 60
--pitch 50
--prefix custom_output_name
--work-dir /path/to/work
```

## 输出文件

脚本会生成：

```text
{prefix}.mp4
{prefix}_with_subtitles.mp4
{prefix}.srt
{prefix}_script.md
{prefix}_timeline.json
{prefix}_verify.txt
```

## 安全说明

- 讯飞凭证只保存到 `~/.codex/secrets/ppt-narration-video-xunfei.json`。
- 密钥文件权限保持 `0600`。
- 如果凭证被粘贴到聊天里，或出现在截图里，用完后应重置密钥。
- Skill 脚本不会打印 API Secret。

## 典型 Codex 提示词

```text
使用 $ppt-narration-video-xunfei 把这个 PDF 做成中文讲解视频。如果没有讲稿，先根据每页内容生成逐页讲稿，并让我确认后再生成配音。
```
