#!/usr/bin/env python3
"""
从 PDF/PPTX 和逐页讲稿生成讯飞配音讲解视频。

功能模块：
1. 读取讯飞凭证 JSON。
2. 将 PDF/PPTX 渲染为逐页 PNG。
3. 解析逐页讲稿。
4. 调用讯飞 WebSocket TTS 生成逐页音频。
5. 合成带字幕轨和无字幕轨 MP4。
6. 输出讲稿、字幕、时间轴，并做媒体流校验。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import ssl
import subprocess
import time
import wave
from dataclasses import dataclass
from email.utils import formatdate
from pathlib import Path
from urllib.parse import quote, urlencode

import fitz
import imageio_ffmpeg
import websocket
from PIL import Image


SECRET_PATH = Path.home() / ".codex" / "secrets" / "ppt-narration-video-xunfei.json"
XFYUN_HOST = "tts-api.xfyun.cn"
XFYUN_PATH = "/v2/tts"
XFYUN_URL = f"wss://{XFYUN_HOST}{XFYUN_PATH}"
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


@dataclass(frozen=True)
class PageScript:
    """单页讲稿数据。"""

    page: int
    title: str
    narration: str


def run(command: list[str]) -> None:
    """执行外部命令；失败时直接抛错，便于暴露根因。"""

    subprocess.run(command, check=True)


def read_secret() -> dict[str, str]:
    """读取讯飞凭证 JSON。"""

    if not SECRET_PATH.exists():
        raise RuntimeError(f"未找到讯飞凭证：{SECRET_PATH}")
    data = json.loads(SECRET_PATH.read_text(encoding="utf-8"))
    for key in ["appid", "apikey", "apisecret"]:
        if not data.get(key):
            raise RuntimeError(f"讯飞凭证缺少字段：{key}")
    return data


def convert_pptx_to_pdf(input_path: Path, work_dir: Path) -> Path:
    """使用 LibreOffice 将 PPTX 转为 PDF。"""

    libreoffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not libreoffice:
        raise RuntimeError("PPTX 输入需要 LibreOffice/soffice 才能转换为 PDF")
    pdf_dir = work_dir / "converted"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    run([libreoffice, "--headless", "--convert-to", "pdf", "--outdir", str(pdf_dir), str(input_path)])
    converted = pdf_dir / f"{input_path.stem}.pdf"
    if not converted.exists():
        raise RuntimeError(f"PPTX 转 PDF 失败：{converted}")
    return converted


def prepare_pdf(input_path: Path, work_dir: Path) -> Path:
    """根据输入类型得到可渲染 PDF。"""

    suffix = input_path.suffix.lower()
    if suffix == ".pdf":
        return input_path
    if suffix in [".pptx", ".ppt"]:
        return convert_pptx_to_pdf(input_path, work_dir)
    raise RuntimeError(f"不支持的输入格式：{input_path.suffix}")


def render_slides(pdf_path: Path, slide_dir: Path) -> int:
    """将 PDF 每页渲染到 1920x1080 白底 PNG。"""

    if slide_dir.exists():
        shutil.rmtree(slide_dir)
    slide_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    for page_index, page in enumerate(doc):
        scale = VIDEO_WIDTH / page.rect.width
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        rendered = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        rendered.thumbnail((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), "white")
        left = (VIDEO_WIDTH - rendered.width) // 2
        top = (VIDEO_HEIGHT - rendered.height) // 2
        canvas.paste(rendered, (left, top))
        canvas.save(slide_dir / f"slide_{page_index + 1:03d}.png", quality=95)
    return doc.page_count


def extract_page_text(pdf_path: Path) -> list[str]:
    """抽取每页文本，用于生成讲稿草稿时参考。"""

    doc = fitz.open(pdf_path)
    return [" ".join(page.get_text("text").split()) for page in doc]


def parse_script(script_path: Path) -> list[PageScript]:
    """解析 Markdown 或普通文本逐页讲稿。"""

    text = script_path.read_text(encoding="utf-8").strip()
    pattern = re.compile(r"(?m)^#{0,3}\s*第\s*(\d+)\s*页[：: ]*(.*?)\s*$")
    matches = list(pattern.finditer(text))
    if not matches:
        raise RuntimeError("讲稿格式无法解析：请使用“## 第1页：标题”这种逐页格式")

    pages: list[PageScript] = []
    for index, match in enumerate(matches):
        page = int(match.group(1))
        title = match.group(2).strip() or f"第{page}页"
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        narration = text[start:end].strip()
        if not narration:
            raise RuntimeError(f"第 {page} 页讲稿为空")
        pages.append(PageScript(page=page, title=title, narration=narration))
    return pages


def create_authorized_url(api_key: str, api_secret: str) -> str:
    """生成讯飞 WebSocket 鉴权 URL。"""

    date = formatdate(timeval=None, localtime=False, usegmt=True)
    signature_origin = f"host: {XFYUN_HOST}\ndate: {date}\nGET {XFYUN_PATH} HTTP/1.1"
    signature_sha = hmac.new(api_secret.encode("utf-8"), signature_origin.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    query = urlencode({"authorization": authorization, "date": date, "host": XFYUN_HOST}, quote_via=quote)
    return f"{XFYUN_URL}?{query}"


def build_tts_payload(appid: str, voice: str, text: str, speed: int, volume: int, pitch: int) -> str:
    """组装讯飞 TTS 请求体。"""

    payload = {
        "common": {"app_id": appid},
        "business": {
            "aue": "lame",
            "auf": "audio/L16;rate=16000",
            "vcn": voice,
            "tte": "UTF8",
            "speed": speed,
            "volume": volume,
            "pitch": pitch,
            "bgs": 0,
        },
        "data": {"status": 2, "text": base64.b64encode(text.encode("utf-8")).decode("utf-8")},
    }
    return json.dumps(payload, ensure_ascii=False)


def synthesize_one(secret: dict[str, str], voice: str, item: PageScript, audio_dir: Path, speed: int, volume: int, pitch: int) -> Path:
    """调用讯飞 TTS 生成单页 WAV；已有文件则复用。"""

    wav_path = audio_dir / f"page_{item.page:03d}.wav"
    mp3_path = audio_dir / f"page_{item.page:03d}.mp3"
    txt_path = audio_dir / f"page_{item.page:03d}.txt"
    if wav_path.exists() and wav_path.stat().st_size > 1000:
        return wav_path

    txt_path.write_text(item.narration, encoding="utf-8")
    audio_chunks: list[bytes] = []
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            ws = websocket.create_connection(
                create_authorized_url(secret["apikey"], secret["apisecret"]),
                sslopt={"cert_reqs": ssl.CERT_REQUIRED},
                timeout=30,
            )
            try:
                ws.send(build_tts_payload(secret["appid"], voice, item.narration, speed, volume, pitch))
                audio_chunks = []
                while True:
                    response = json.loads(ws.recv())
                    if response.get("code") != 0:
                        raise RuntimeError(f"讯飞合成失败：page={item.page}, response={response}")
                    data = response.get("data") or {}
                    if data.get("audio"):
                        audio_chunks.append(base64.b64decode(data["audio"]))
                    if data.get("status") == 2:
                        break
            finally:
                ws.close()
            break
        except Exception as exc:
            last_error = exc
            print(f"第 {item.page:02d} 页第 {attempt} 次合成失败：{exc}")
            time.sleep(attempt * 2)
    else:
        raise RuntimeError(f"第 {item.page:02d} 页讯飞合成连续失败") from last_error

    mp3_path.write_bytes(b"".join(audio_chunks))
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3_path), "-ar", "44100", "-ac", "2", str(wav_path)])
    return wav_path


def wav_duration_seconds(path: Path) -> float:
    """读取 WAV 时长。"""

    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / float(audio.getframerate())


def format_srt_time(seconds: float) -> str:
    """将秒数转换为 SRT 时间格式。"""

    milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def compose_video(items: list[PageScript], slide_dir: Path, audio_dir: Path, segment_dir: Path, output_dir: Path, prefix: str) -> dict[str, str]:
    """合成逐页片段、字幕、时间轴和最终 MP4。"""

    if segment_dir.exists():
        shutil.rmtree(segment_dir)
    segment_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    timeline = []
    srt_blocks = []
    cursor = 0.0
    for item in items:
        image_file = slide_dir / f"slide_{item.page:03d}.png"
        wav_file = audio_dir / f"page_{item.page:03d}.wav"
        segment_file = segment_dir / f"segment_{item.page:03d}.mp4"
        segment_duration = wav_duration_seconds(wav_file) + 0.35
        run(
            [
                FFMPEG,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-loop",
                "1",
                "-i",
                str(image_file),
                "-i",
                str(wav_file),
                "-t",
                f"{segment_duration:.3f}",
                "-vf",
                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:white,fps={FPS},format=yuv420p",
                "-af",
                "apad=pad_dur=0.35",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-shortest",
                str(segment_file),
            ]
        )
        start = cursor
        end = cursor + segment_duration
        cursor = end
        timeline.append({"page": item.page, "title": item.title, "start": round(start, 3), "end": round(end, 3), "duration": round(segment_duration, 3), "narration": item.narration})
        srt_blocks.append(f"{item.page}\n{format_srt_time(start)} --> {format_srt_time(end)}\n{item.narration}\n")

    concat_file = segment_dir / "concat.txt"
    concat_file.write_text("\n".join([f"file '{(segment_dir / f'segment_{item.page:03d}.mp4').resolve()}'" for item in items]), encoding="utf-8")
    no_subtitle_mp4 = output_dir / f"{prefix}.mp4"
    final_mp4 = output_dir / f"{prefix}_with_subtitles.mp4"
    subtitle_file = output_dir / f"{prefix}.srt"
    timeline_file = output_dir / f"{prefix}_timeline.json"
    script_file = output_dir / f"{prefix}_script.md"

    subtitle_file.write_text("\n".join(srt_blocks), encoding="utf-8")
    timeline_file.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    script_file.write_text("\n\n".join([f"## 第{item.page}页：{item.title}\n\n{item.narration}" for item in items]), encoding="utf-8")
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(no_subtitle_mp4)])
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(no_subtitle_mp4), "-i", str(subtitle_file), "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=chi", str(final_mp4)])
    return {"video": str(no_subtitle_mp4), "video_with_subtitles": str(final_mp4), "srt": str(subtitle_file), "timeline": str(timeline_file), "script": str(script_file)}


def ffprobe_summary(video_path: Path) -> str:
    """返回 ffmpeg 媒体流摘要。"""

    result = subprocess.run([FFMPEG, "-hide_banner", "-i", str(video_path)], text=True, capture_output=True)
    return result.stderr


def main() -> None:
    """命令行入口。"""

    parser = argparse.ArgumentParser(description="生成讯飞配音 PPT/PDF 讲解视频")
    parser.add_argument("--input", required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--voice", default=None)
    parser.add_argument("--speed", type=int, default=50)
    parser.add_argument("--volume", type=int, default=60)
    parser.add_argument("--pitch", type=int, default=50)
    parser.add_argument("--prefix", default=None)
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve() if args.work_dir else output_dir.parent / "work" / f"{input_path.stem}_video_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    secret = read_secret()
    voice = args.voice or secret.get("default_voice") or "x4_lingfeizhe_zl"
    prefix = args.prefix or f"{input_path.stem}_xunfei_{voice}"

    pdf_path = prepare_pdf(input_path, work_dir)
    slide_dir = work_dir / "slides"
    page_count = render_slides(pdf_path, slide_dir)
    items = parse_script(Path(args.script).expanduser().resolve())
    if len(items) != page_count:
        raise RuntimeError(f"讲稿页数 {len(items)} 与页面数量 {page_count} 不一致")

    audio_dir = work_dir / f"audio_{voice}"
    audio_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        print(f"生成第 {item.page:02d} 页讯飞配音")
        synthesize_one(secret, voice, item, audio_dir, args.speed, args.volume, args.pitch)

    outputs = compose_video(items, slide_dir, audio_dir, work_dir / f"segments_{voice}", output_dir, prefix)
    summary = ffprobe_summary(Path(outputs["video_with_subtitles"]))
    (output_dir / f"{prefix}_verify.txt").write_text(summary, encoding="utf-8")
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
