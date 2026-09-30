"""发音服务单元测试：服务端 TTS、缓存命中、超时 / 404 / 异常降级、失败不留半文件。"""

from __future__ import annotations

import httpx
import pytest

from app.services import pronounce_service

pytestmark = pytest.mark.unit

SENTENCE = "I have an apple and the apple is red."


class _FakeResponse:
    def __init__(self, status_code: int = 200, content: bytes = b"ID3-audio", content_type: str = "audio/mpeg"):
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    from app.config import settings

    target = tmp_path / "pronounce"
    monkeypatch.setattr(settings, "pronounce_cache_dir", str(target))
    return target


def cache_file(cache_dir, text: str):
    return cache_dir / f"{pronounce_service.cache_key(text)}.mp3"


def test_success_writes_cache_and_returns_bytes(cache_dir, monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    content = pronounce_service.fetch_pronunciation("ability")
    assert content == b"ID3-audio"
    assert cache_file(cache_dir, "ability").exists()

    # 第二次命中缓存，不再访问上游
    pronounce_service.fetch_pronunciation("ability")
    assert len(calls) == 1


def test_upstream_404_falls_back_without_cache(cache_dir, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: _FakeResponse(404, b""))

    with pytest.raises(pronounce_service.PronunciationUnavailable):
        pronounce_service.fetch_pronunciation("ability")
    assert not cache_file(cache_dir, "ability").exists()


def test_timeout_is_swallowed_to_unavailable(cache_dir, monkeypatch):
    def fake_get(url, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(pronounce_service.PronunciationUnavailable):
        pronounce_service.fetch_pronunciation("ability")
    assert not cache_file(cache_dir, "ability").exists()


def test_non_audio_content_type_is_rejected(cache_dir, monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda url, **kwargs: _FakeResponse(200, b"<html>", "text/html")
    )

    with pytest.raises(pronounce_service.PronunciationUnavailable):
        pronounce_service.fetch_pronunciation("ability")


def test_invalid_word_is_rejected_without_request(cache_dir, monkeypatch):
    def fake_get(url, **kwargs):  # pragma: no cover - 不应被调用
        raise AssertionError("不应发起请求")

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(pronounce_service.PronunciationUnavailable):
        pronounce_service.fetch_pronunciation("../../etc/passwd")


def test_speakable_text_keeps_english_only():
    assert pronounce_service.speakable_text("talk about 谈论") == "talk about"
    assert (
        pronounce_service.speakable_text("have the ability to do 有能力做")
        == "have the ability to do"
    )
    assert pronounce_service.speakable_text("ability") == "ability"
    assert pronounce_service.speakable_text("只有中文") == ""


def test_phrase_pronunciation_uses_english_part(cache_dir, monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    pronounce_service.fetch_pronunciation("talk about 谈论")
    assert "talk%20about" in calls[0] or "talk+about" in calls[0]
    assert cache_file(cache_dir, "talk about").exists()


def test_phrase_without_english_is_unavailable(cache_dir, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: _FakeResponse())

    with pytest.raises(pronounce_service.PronunciationUnavailable):
        pronounce_service.fetch_pronunciation("只有中文释义")


def test_sentence_is_synthesized_by_server_tts(cache_dir, monkeypatch):
    """例句（含标点、超出上游长度）由服务端 TTS 合成，不再回退上游。"""
    monkeypatch.setattr(pronounce_service, "synthesize_edge", lambda text: b"EDGE-AUDIO")

    def fake_get(url, **kwargs):  # pragma: no cover - 例句不应走上游
        raise AssertionError("例句不应回退到上游")

    monkeypatch.setattr(httpx, "get", fake_get)

    assert pronounce_service.fetch_pronunciation(SENTENCE) == b"EDGE-AUDIO"
    assert cache_file(cache_dir, SENTENCE).exists()

    # 第二次命中缓存，不再合成
    calls = []
    monkeypatch.setattr(
        pronounce_service,
        "synthesize_edge",
        lambda text: (calls.append(text), b"EDGE-AUDIO")[1],
    )
    pronounce_service.fetch_pronunciation(SENTENCE)
    assert not calls


def test_tts_failure_falls_back_to_upstream(cache_dir, monkeypatch):
    """TTS 不可用时，单词仍可从上游取得发音。"""
    monkeypatch.setattr(pronounce_service, "synthesize_edge", lambda text: None)
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: _FakeResponse())

    assert pronounce_service.fetch_pronunciation("ability") == b"ID3-audio"


def test_overlong_text_is_unavailable(cache_dir, monkeypatch):
    monkeypatch.setattr(pronounce_service, "synthesize_edge", lambda text: b"EDGE")
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: _FakeResponse())

    with pytest.raises(pronounce_service.PronunciationUnavailable):
        pronounce_service.fetch_pronunciation("a " * 200)
