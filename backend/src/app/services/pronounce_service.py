"""发音服务：服务端 TTS（edge-tts）+ 第三方公共发音接口兜底 + 磁盘缓存。

优先用 edge-tts 合成整句，单词与例句音色统一，且不依赖浏览器语音合成
（不支持 speechSynthesis 的设备同样可播放）；edge-tts 不可用时回退
有道 dictvoice（仅支持单词 / 短短语）。两者都失败则抛
:class:`PronunciationUnavailable`，由接口层转为 404，前端据此降级为浏览器语音。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

import httpx

from app.config import settings
from app.errors import AppError

logger = logging.getLogger(__name__)

SAFE_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z\-' ]{0,119}$")
# 短语形如 "have the ability to do 有能力做"：只保留首个非 ASCII 之前的英文部分
NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")
# 送 TTS 的文本长度上限，避免超长文本拖慢请求
MAX_TEXT_CHARS = 200


def speakable_text(text: str) -> str:
    """取可朗读文本：短语只朗读英文部分（中文释义仅作注释）。"""
    value = (text or "").strip()
    english = NON_ASCII_RE.split(value)[0]
    english = re.sub(r"\s+", " ", english).strip(" -'")
    return english


class PronunciationUnavailable(AppError):
    def __init__(self, message: str | None = None):
        super().__init__("pronunciation_unavailable", message, status_code=404)


def cache_key(text: str) -> str:
    """缓存键：可读前缀 + 摘要。

    例句含空格与标点，直接当文件名在 Windows 上不合法，故做摘要化处理。
    """
    normalized = " ".join((text or "").split()).lower()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "_", normalized)[:40].strip("_")
    return f"{slug}_{digest}" if slug else digest


def cache_path_for(text: str) -> Path:
    directory = Path(settings.pronounce_cache_dir)
    return directory / f"{cache_key(text)}.mp3"


def read_cache(text: str) -> bytes | None:
    path = cache_path_for(text)
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes()
    return None


def _write_cache(text: str, content: bytes) -> None:
    """原子写入缓存：先写临时文件再替换，失败不留半成品。"""
    path = cache_path_for(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(content)
        os.replace(tmp_name, path)
    except Exception:  # pragma: no cover - 磁盘异常时降级即可
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def synthesize_edge(text: str) -> bytes | None:
    """用 edge-tts 合成音频（单词与整句皆可）；不可用 / 超时返回 None。"""
    try:
        import edge_tts
    except Exception as exc:  # pragma: no cover - 依赖缺失时直接兜底
        logger.warning("edge-tts 不可用: %s", exc)
        return None

    async def _run() -> bytes:
        communicate = edge_tts.Communicate(
            text, settings.tts_voice, rate=settings.tts_rate
        )
        chunks: list[bytes] = []
        async for part in communicate.stream():
            if part.get("type") == "audio":
                chunks.append(part["data"])
        return b"".join(chunks)

    try:
        data = asyncio.run(
            asyncio.wait_for(_run(), timeout=settings.tts_timeout_seconds)
        )
    except Exception as exc:
        logger.warning("edge-tts 合成失败(%.32s): %s", text, exc)
        return None
    return data or None


def _fetch_upstream(word: str) -> bytes | None:
    """有道 dictvoice 兜底：整句上游返回 500，故只在单词 / 短短语时使用。"""
    url = settings.pronounce_upstream_url.format(word=quote(word))
    try:
        response = httpx.get(
            url,
            timeout=settings.pronounce_timeout_seconds,
            follow_redirects=True,
        )
    except Exception as exc:
        logger.info("发音上游异常(%.32s): %s", word, exc)
        return None

    content_type = response.headers.get("content-type", "")
    if response.status_code != 200 or not response.content:
        return None
    if content_type and not content_type.lower().startswith("audio"):
        return None
    return response.content


def fetch_pronunciation(word: str) -> bytes:
    """取得单词 / 例句发音音频字节；命中缓存则不访问网络。"""
    value = speakable_text(word)
    if not value or len(value) > MAX_TEXT_CHARS:
        raise PronunciationUnavailable()

    cached = read_cache(value)
    if cached is not None:
        return cached

    content = synthesize_edge(value)
    if content:
        _write_cache(value, content)
        return content

    # 兜底：有道只认单词 / 短短语（整句上游返回 500 returned null audio）
    if SAFE_WORD_RE.fullmatch(value):
        fallback = _fetch_upstream(value)
        if fallback:
            _write_cache(value, fallback)
            return fallback

    raise PronunciationUnavailable()
