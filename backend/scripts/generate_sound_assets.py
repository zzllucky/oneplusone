"""音效音源生成脚本（004-sound-effects，**仅开发期使用，不进镜像**）。

用途：用项目已有的 TTS 引擎（edge-tts，发音功能已在用）把 18 条英文短句预合成为
mp3，输出到 `frontend/public/sounds/`，并生成 `manifest.json`（事件 / 文件 / 台词 /
时长 / 体积），供前端播放、契约测试与排查使用。

为什么预生成：运行时只播放本地文件，才能做到离线可用、零外部请求、点击即响
（见 specs/004-sound-effects/research.md R-001）。生成的 mp3 随 `frontend/dist`
一起打包发布，不在本脚本里上传任何内容。

用法（默认需联网，在 backend venv 下执行）：
    .venv/Scripts/python.exe scripts/generate_sound_assets.py
    .venv/Scripts/python.exe scripts/generate_sound_assets.py --voice en-US-GuyNeural --rate +15% --pitch +8Hz

自备音源（把自己的 mp3 放进 frontend/public/sounds/ 后只登记，不联网、不覆盖原文件）：
    .venv/Scripts/python.exe scripts/generate_sound_assets.py --manifest-only
    .venv/Scripts/python.exe scripts/generate_sound_assets.py --manifest-only --max-duration-ms 3000 --max-bytes 61440

文件名必须与 SOUND_LINES 的第三列一致（page_home.mp3、streak_1.mp3 …），
否则前端找不到音源；自备音源较长/较大时用 --max-* 放宽阈值，阈值会写入 manifest
供契约测试读取。

失败即退出（非 0），不写半成品：任何一条缺失或合成失败都会中断，避免生成残缺音源。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# 18 条台词：与 specs/004-sound-effects/contracts/sound-assets.md 第 3 节逐字一致。
# 改台词只需改这里后重跑脚本（事件标识与文件名保持不变，触发逻辑不受影响）。
SOUND_LINES: list[tuple[str, str, str]] = [
    ("page.home", "Stick together, team.", "page_home.mp3"),
    ("page.study", "OK, let's go!", "page_study.mp3"),
    ("page.quiz", "Fire in the hole!", "page_quiz.mp3"),
    ("page.wrong", "Bombs on the ground here.", "page_wrong.mp3"),
    ("page.summary", "Keep going and stay strong, team.", "page_summary.mp3"),
    ("quiz.start", "Come get some!", "quiz_start.mp3"),
    ("streak.1", "First blood", "streak_1.mp3"),
    ("streak.2", "Double kill", "streak_2.mp3"),
    ("streak.3", "Triple kill", "streak_3.mp3"),
    ("streak.4", "Quadra kill", "streak_4.mp3"),
    ("streak.5", "Penta kill", "streak_5.mp3"),
    ("streak.6", "Hexa kill", "streak_6.mp3"),
    ("streak.7", "Hepta kill", "streak_7.mp3"),
    ("streak.8", "Octa kill", "streak_8.mp3"),
    ("streak.9", "Nona kill", "streak_9.mp3"),
    ("streak.10", "Deca kill", "streak_10.mp3"),
    ("streak.extend", "Good job", "streak_extend.mp3"),
    ("answer.wrong", "Storm the front.", "answer_wrong.mp3"),
]

MANIFEST_VERSION = 1
# 契约阈值：单条 ≤2 秒、≤30 KB（contracts/sound-assets.md 第 5 节）
MAX_DURATION_MS = 2000
MAX_BYTES = 30 * 1024
# edge-tts 默认输出为 96 kbps CBR 单声道 mp3：96000 bit/s ÷ 8 = 12000 B/s。
# 无 mutagen 时按此估算时长（含文件头，误差数十毫秒，用于阈值校验足够）。
BYTES_PER_SECOND = 12000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成音效音源（自产英文短句语音）")
    parser.add_argument("--voice", default="en-US-GuyNeural", help="TTS 音色（激情男声）")
    parser.add_argument("--rate", default="+15%", help="语速（正值为偏快）")
    parser.add_argument("--pitch", default="+8Hz", help="音高（正值为上扬）")
    parser.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parents[2] / "frontend" / "public" / "sounds"),
        help="输出目录（默认 frontend/public/sounds）",
    )
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="不联网合成：按目录里已放好的 mp3 重新登记 manifest（自备音源时用）",
    )
    parser.add_argument(
        "--max-duration-ms",
        type=int,
        default=MAX_DURATION_MS,
        help=f"单条时长上限，超过仅告警（默认 {MAX_DURATION_MS}ms）",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=MAX_BYTES,
        help=f"单条体积上限，超过仅告警（默认 {MAX_BYTES}B）",
    )
    return parser.parse_args()


def duration_ms(path: Path) -> int:
    """优先用 mutagen 读真实时长，缺失则按 96kbps CBR 估算。"""
    try:
        from mutagen.mp3 import MP3  # type: ignore

        return int(MP3(path).info.length * 1000)
    except Exception:
        return int(path.stat().st_size / BYTES_PER_SECOND * 1000)


async def synthesize(text: str, voice: str, rate: str, pitch: str) -> bytes:
    """合成单条语音；依赖缺失或失败时抛异常（由调用方中断整个生成）。"""
    try:
        import edge_tts
    except Exception as exc:  # pragma: no cover - 依赖缺失属环境问题
        raise RuntimeError(f"edge-tts 不可用：{exc}") from exc

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    chunks: list[bytes] = []
    async for part in communicate.stream():
        if part.get("type") == "audio":
            chunks.append(part["data"])
    data = b"".join(chunks)
    if not data:
        raise RuntimeError("合成结果为空")
    return data


async def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    warnings: list[str] = []

    for event, text, filename in SOUND_LINES:
        target = out_dir / filename
        if args.manifest_only:
            # 自备音源：只登记，不联网、不覆盖用户放好的文件
            if not target.is_file() or target.stat().st_size == 0:
                print(
                    f"[FAIL] {event} ({filename}): 缺少音源，请先放入 {out_dir}",
                    file=sys.stderr,
                )
                return 1
        else:
            try:
                data = await synthesize(text, args.voice, args.rate, args.pitch)
            except Exception as exc:
                print(f"[FAIL] {event} ({filename}): {exc}", file=sys.stderr)
                return 1
            target.write_bytes(data)

        size = target.stat().st_size
        millis = duration_ms(target)
        if millis > args.max_duration_ms:
            warnings.append(f"{filename} 时长 {millis}ms 超过 {args.max_duration_ms}ms")
        if size > args.max_bytes:
            warnings.append(f"{filename} 体积 {size}B 超过 {args.max_bytes}B")
        entries.append(
            {
                "event": event,
                "file": filename,
                "text": text,
                "duration_ms": millis,
                "bytes": size,
            }
        )
        print(f"[OK] {filename:<20} {millis:>5}ms {size:>7}B  {text}")

    manifest = {
        "version": MANIFEST_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "voice": "custom（自备音源）" if args.manifest_only else args.voice,
        "rate": "custom" if args.manifest_only else args.rate,
        "pitch": "custom" if args.manifest_only else args.pitch,
        "thresholds": {
            "max_duration_ms": args.max_duration_ms,
            "max_bytes": args.max_bytes,
        },
        "entries": entries,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    total = sum(item["bytes"] for item in entries)
    print(f"\n共 {len(entries)} 条，总计 {total} B（{total / 1024:.1f} KB）→ {out_dir}")
    for line in warnings:
        print(f"[WARN] {line}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
