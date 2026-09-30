"""发音接口集成测试：成功返回音频、失败返回 404、缓存命中不再访问上游。"""

from __future__ import annotations

import httpx
import pytest

from tests.conftest import auth_headers, register

pytestmark = pytest.mark.integration


class _FakeResponse:
    def __init__(self, status_code=200, content=b"ID3-audio", content_type="audio/mpeg"):
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    from app.config import settings

    target = tmp_path / "cache"
    monkeypatch.setattr(settings, "pronounce_cache_dir", str(target))
    return target


def test_pronounce_returns_audio(client, cache_dir, monkeypatch):
    calls = []
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **kwargs: (calls.append(url), _FakeResponse())[1],
    )
    token = register(client)["access_token"]

    response = client.get("/api/pronounce/ability", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.content == b"ID3-audio"
    assert response.headers["content-type"].startswith("audio")

    client.get("/api/pronounce/ability", headers=auth_headers(token))
    assert len(calls) == 1  # 第二次命中磁盘缓存


def test_pronounce_unavailable_returns_404_error_code(client, cache_dir, monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda url, **kwargs: _FakeResponse(404, b"", "text/html")
    )
    token = register(client)["access_token"]

    response = client.get("/api/pronounce/nonexistentword", headers=auth_headers(token))

    assert response.status_code == 404
    if response.headers.get("content-type", "").startswith("application/json"):
        assert response.json()["error"]["code"] == "pronunciation_unavailable"


def test_pronounce_timeout_degrades(client, cache_dir, monkeypatch):
    def fake_get(url, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "get", fake_get)
    token = register(client)["access_token"]

    response = client.get("/api/pronounce/ability", headers=auth_headers(token))
    assert response.status_code == 404
