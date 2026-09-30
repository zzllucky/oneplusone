"""错题专项练习契约测试（contracts/api.md —— Review 段）。"""

from __future__ import annotations

import pytest

from tests.conftest import (
    auth_headers,
    register,
    view_all_today,
)

pytestmark = pytest.mark.contract


def _answer(client, headers, question_id, choice_index) -> dict:
    return client.post(
        "/api/quiz/review/answer",
        headers=headers,
        json={"question_id": question_id, "choice_index": choice_index},
    ).json()


def _clear_from_wrong_book(client, headers, question_id) -> dict:
    """连续两次提交正确答案（中间不能答错，否则 streak 归零）。"""
    probe = _answer(client, headers, question_id, 0)
    if not probe["is_correct"]:
        # 探测性作答答错会归零 streak，随后连续两次答对即可移出
        probe = _answer(client, headers, question_id, probe["correct_index"])
    return _answer(client, headers, question_id, probe["correct_index"])


def _seed_wrong_words(client, headers, token) -> list[int]:
    """通过今日测验答错制造两条错题，返回错题 word_id 列表。"""
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()
    targets = start["questions"][:2]

    for question in targets:
        probe = client.post(
            "/api/quiz/today/answer",
            headers=headers,
            json={"question_id": question["question_id"], "choice_index": 0},
        ).json()
        if not probe["is_correct"]:
            continue
        wrong_index = next(index for index in range(4) if index != probe["correct_index"])
        client.post(
            "/api/quiz/today/answer",
            headers=headers,
            json={"question_id": question["question_id"], "choice_index": wrong_index},
        )
    return [question["word_id"] for question in targets]


def test_review_start_with_empty_wrong_book_returns_409(client):
    token = register(client)["access_token"]

    response = client.post("/api/quiz/review/start", headers=auth_headers(token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_wrong_words"


def test_review_questions_only_from_wrong_book(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token)

    response = client.post("/api/quiz/review/start", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert sorted(question["word_id"] for question in body["questions"]) == sorted(
        seeded
    )


def test_review_answer_removes_only_after_streak(client):
    """答对 1 次只累计 streak（保留），连续答对 2 次才移出错题本。"""
    token = register(client)["access_token"]
    headers = auth_headers(token)
    _seed_wrong_words(client, headers, token)
    start = client.post("/api/quiz/review/start", headers=headers).json()
    question = start["questions"][0]

    probe = client.post(
        "/api/quiz/review/answer",
        headers=headers,
        json={"question_id": question["question_id"], "choice_index": 0},
    )
    assert probe.status_code == 200
    body = probe.json()
    assert set(body) == {
        "question_id",
        "is_correct",
        "correct_index",
        "removed_from_wrong_words",
        "added_back_to_wrong_words",
        "correct_streak",
    }

    if not body["is_correct"]:
        assert body["removed_from_wrong_words"] is False
        assert body["added_back_to_wrong_words"] is False
        body = client.post(
            "/api/quiz/review/answer",
            headers=headers,
            json={
                "question_id": question["question_id"],
                "choice_index": body["correct_index"],
            },
        ).json()

    # 第一次答对：保留在错题本，streak = 1
    assert body["is_correct"] is True
    assert body["removed_from_wrong_words"] is False
    assert body["correct_streak"] == 1

    # 第二次答对：达到阈值 → 移出
    second = client.post(
        "/api/quiz/review/answer",
        headers=headers,
        json={
            "question_id": question["question_id"],
            "choice_index": body["correct_index"],
        },
    ).json()
    assert second["removed_from_wrong_words"] is True
    assert second["correct_streak"] == 0


def test_review_finish_report_contains_remaining_count(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    _seed_wrong_words(client, headers, token)
    start = client.post("/api/quiz/review/start", headers=headers).json()

    for question in start["questions"]:
        _clear_from_wrong_book(client, headers, question["question_id"])

    response = client.post("/api/quiz/review/finish", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["correct_count"] == 2
    assert body["remaining_wrong_count"] == 0


def test_review_requires_authentication(client):
    assert client.post("/api/quiz/review/answer", json={}).status_code == 401
    assert client.post("/api/quiz/review/finish").status_code == 401
