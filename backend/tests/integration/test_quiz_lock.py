"""测验解锁守卫：未全部浏览时任何进入方式都被拒绝。"""

from __future__ import annotations

import pytest

from tests.conftest import (
    auth_headers,
    register,
    today_word_ids,
    view_all_today,
)

pytestmark = pytest.mark.integration


def test_start_rejected_when_only_partially_viewed(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    word_ids = today_word_ids(client, token)

    for word_id in word_ids[:10]:
        client.post(f"/api/study/today/items/{word_id}/view", headers=headers)

    today = client.get("/api/study/today", headers=headers).json()
    assert today["quiz_unlocked"] is False

    response = client.post("/api/quiz/today/start", headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "quiz_locked"


def test_direct_access_without_any_view_is_rejected(client):
    token = register(client)["access_token"]

    response = client.post("/api/quiz/today/start", headers=auth_headers(token))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "quiz_locked"


def test_start_allowed_after_all_viewed(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    view_all_today(client, token)

    response = client.post("/api/quiz/today/start", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["questions"]) == 20


def test_answering_without_start_is_not_found(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    view_all_today(client, token)

    response = client.post(
        "/api/quiz/today/answer",
        headers=headers,
        json={"question_id": 1, "choice_index": 0},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "attempt_not_found"
