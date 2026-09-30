"""今日学习链路：生成、稳定、浏览进度、幂等、解锁。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, register, today_word_ids

pytestmark = pytest.mark.integration


def test_today_set_is_generated_once_and_stable(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)

    first = client.get("/api/study/today", headers=headers).json()
    second = client.get("/api/study/today", headers=headers).json()

    assert first["total_count"] == 20
    assert [item["word_id"] for item in first["items"]] == [
        item["word_id"] for item in second["items"]
    ]
    assert first["study_date"] == second["study_date"]


def test_marking_viewed_advances_progress(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    word_ids = today_word_ids(client, token)

    for index, word_id in enumerate(word_ids, start=1):
        response = client.post(
            f"/api/study/today/items/{word_id}/view", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["viewed_count"] == index

    today = client.get("/api/study/today", headers=headers).json()
    assert today["all_viewed"] is True
    assert today["quiz_unlocked"] is True


def test_view_twice_is_idempotent(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    word_id = today_word_ids(client, token)[0]

    first = client.post(f"/api/study/today/items/{word_id}/view", headers=headers).json()
    second = client.post(
        f"/api/study/today/items/{word_id}/view", headers=headers
    ).json()

    assert first["viewed_count"] == second["viewed_count"] == 1

    items = client.get("/api/study/today", headers=headers).json()["items"]
    viewed_at = next(item["viewed_at"] for item in items if item["word_id"] == word_id)
    assert viewed_at  # 首次时间被保留


def test_goal_smaller_than_library(client):
    token = register(client, login_name="stu01")["access_token"]
    headers = auth_headers(token)
    client.put("/api/settings", headers=headers, json={"daily_goal": 5})

    body = client.get("/api/study/today", headers=headers).json()
    assert body["total_count"] == 5
    assert body["library_exhausted"] is False
