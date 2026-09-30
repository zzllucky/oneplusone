"""测验接口契约测试（contracts/api.md —— Quiz 段）。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, register, today_word_ids, view_all_today

pytestmark = pytest.mark.contract


def test_start_is_locked_before_all_words_viewed(client):
    token = register(client)["access_token"]
    client.post(
        f"/api/study/today/items/{today_word_ids(client, token)[0]}/view",
        headers=auth_headers(token),
    )

    response = client.post("/api/quiz/today/start", headers=auth_headers(token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "quiz_locked"


def test_start_returns_questions_without_answer(client):
    token = register(client)["access_token"]
    view_all_today(client, token)

    response = client.post("/api/quiz/today/start", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["attempt_id"]
    assert len(body["questions"]) == 20
    question = body["questions"][0]
    assert set(question) == {"question_id", "word_id", "type", "prompt", "options"}
    assert len(question["options"]) == 4
    assert question["type"] in ("en2zh", "zh2en")
    assert "correct_index" not in question  # 正确答案不下发


def test_answer_returns_correct_index_and_wrong_word_flag(client):
    token = register(client)["access_token"]
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=auth_headers(token)).json()
    question = start["questions"][0]

    # 先故意答错（选一个非正确项），通过返回的 correct_index 定位正确项
    probe = client.post(
        "/api/quiz/today/answer",
        headers=auth_headers(token),
        json={"question_id": question["question_id"], "choice_index": 0},
    )
    assert probe.status_code == 200
    body = probe.json()
    assert set(body) == {
        "question_id",
        "is_correct",
        "correct_index",
        "added_to_wrong_words",
    }
    assert isinstance(body["is_correct"], bool)
    if not body["is_correct"]:
        assert body["added_to_wrong_words"] is True

    # 用正确项重答：答对不得移除错题
    correct = client.post(
        "/api/quiz/today/answer",
        headers=auth_headers(token),
        json={
            "question_id": question["question_id"],
            "choice_index": body["correct_index"],
        },
    )
    assert correct.status_code == 200
    assert correct.json()["is_correct"] is True
    assert correct.json()["added_to_wrong_words"] is False


def test_finish_returns_report(client):
    token = register(client)["access_token"]
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=auth_headers(token)).json()

    for question in start["questions"]:
        client.post(
            "/api/quiz/today/answer",
            headers=auth_headers(token),
            json={"question_id": question["question_id"], "choice_index": 0},
        )

    response = client.post("/api/quiz/today/finish", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    for key in (
        "attempt_id",
        "total_count",
        "correct_count",
        "wrong_count",
        "accuracy",
        "duration_seconds",
        "new_wrong_words",
    ):
        assert key in body
    assert body["total_count"] == 20
    assert body["correct_count"] + body["wrong_count"] == body["total_count"]
    assert isinstance(body["new_wrong_words"], list)


def test_quiz_requires_authentication(client):
    assert client.post("/api/quiz/today/start").status_code == 401
    assert client.post("/api/quiz/review/start").status_code == 401
