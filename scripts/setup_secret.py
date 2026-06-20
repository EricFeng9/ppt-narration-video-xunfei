#!/usr/bin/env python3
"""
保存讯飞 TTS 凭证到用户本机私有配置文件。

功能模块：
1. 接收 APPID、APIKey、APISecret、默认发音人。
2. 写入 ~/.codex/secrets/ppt-narration-video-xunfei.json。
3. 设置文件权限为 0600，减少误泄漏风险。
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


SECRET_PATH = Path.home() / ".codex" / "secrets" / "ppt-narration-video-xunfei.json"


def main() -> None:
    """命令行入口。"""

    parser = argparse.ArgumentParser(description="保存讯飞语音合成 API 凭证")
    parser.add_argument("--appid", required=True)
    parser.add_argument("--apikey", required=True)
    parser.add_argument("--apisecret", required=True)
    parser.add_argument("--voice", default="x4_lingfeizhe_zl")
    args = parser.parse_args()

    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    SECRET_PATH.write_text(
        json.dumps(
            {
                "appid": args.appid,
                "apikey": args.apikey,
                "apisecret": args.apisecret,
                "default_voice": args.voice,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    os.chmod(SECRET_PATH, 0o600)
    print(f"saved: {SECRET_PATH}")


if __name__ == "__main__":
    main()
