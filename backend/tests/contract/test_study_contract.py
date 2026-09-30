"""学习接口契约测试（contracts/api.md —— Study 段）。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, register, today_word_ids

pytestmark = pytest.mark.contract


def test_today_study_shape(client):
    token = register(client)["access_token"]

    response = client.get("/api/study/today", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    for key in (
        "study_date",
        "total_count",
        "viewed_count",
        "all_viewed",
        "quiz_unlocked",
        "library_exhausted",
        "items",
    ):
        assert key in body

    assert body["viewed_count"] == 0
    assert body["all_viewed"] is False
    assert body["quiz_unlocked"] is False
    assert len(body["items"]) == body["total_count"]

    first = body["items"][0]
    for key in (
        "word_id",
        "spelling",
        "meaning_zh",
        "phrase",
        "phonetic",
        "order_index",
        "viewed_at",
    ):
        assert key in first
    assert first["viewed_at"] is None


def test_view_word_response_shape(client):
    token = register(client)["access_token"]
    word_id = today_word_ids(client, token)[0]

    response = client.post(
        f"/api/study/today/items/{word_id}/view", headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["word_id"] == word_id
    assert body["viewed_count"] == 1
    assert body["quiz_unlocked"] is False


def test_view_word_outside_today_set_returns_404(client):
    token = register(client)["access_token"]
    known = set(today_word_ids(client, token))
    foreign = next(index for index in range(1, 5000) if index not in known)

    response = client.post(
        f"/api/study/today/items/{foreign}/view", headers=auth_headers(token)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "word_not_in_today_set"


def test_study_requires_authentication(client):
    assert client.get("/api/study/today").status_code == 401
    assert client.post("/api/study/today/items/1/view").status_code == 401
    assert client.get("/api/pronounce/ability").status_code == 401
