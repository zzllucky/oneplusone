"""今日测验全链路 —— 含「答对不删错题」硬性约束的回归护栏。"""

from __future__ import annotations

import pytest

from tests.conftest import (
    auth_headers,
    register,
    view_all_today,
    wrong_word_ids,
)

pytestmark = pytest.mark.integration


def _answer(client, headers, question_id, choice_index) -> dict:
    response = client.post(
        "/api/quiz/today/answer",
        headers=headers,
        json={"question_id": question_id, "choice_index": choice_index},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _force_wrong(client, headers, question_id) -> None:
    probe = _answer(client, headers, question_id, 0)
    if probe["is_correct"]:
        wrong_index = next(index for index in range(4) if index != probe["correct_index"])
        _answer(client, headers, question_id, wrong_index)


def _force_correct(client, headers, question_id) -> dict:
    probe = _answer(client, headers, question_id, 0)
    if probe["is_correct"]:
        return probe
    return _answer(client, headers, question_id, probe["correct_index"])


def test_wrong_answer_adds_to_wrong_book(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()

    targets = start["questions"][:3]
    for question in targets:
        _force_wrong(client, headers, question["question_id"])

    stored = wrong_word_ids(client, token)
    assert sorted(stored) == sorted(question["word_id"] for question in targets)


def test_correct_answer_in_daily_quiz_never_removes_wrong_word(client):
    """FR-026 回归护栏：今日测验答对，错题本记录必须仍然存在。"""
    token = register(client)["access_token"]
    headers = auth_headers(token)
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()

    target = start["questions"][0]
    _force_wrong(client, headers, target["question_id"])
    assert target["word_id"] in wrong_word_ids(client, token)

    result = _force_correct(client, headers, target["question_id"])
    assert result["is_correct"] is True
    assert result["added_to_wrong_words"] is False

    assert target["word_id"] in wrong_word_ids(client, token), (
        "今日测验答对不得移除错题本记录"
    )


def test_repeated_wrong_answer_keeps_single_record_and_first_time(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()

    target = start["questions"][0]
    _force_wrong(client, headers, target["question_id"])
    first_added_at = client.get("/api/wrong-words", headers=headers).json()["items"][0][
        "added_at"
    ]

    _force_wrong(client, headers, target["question_id"])
    body = client.get("/api/wrong-words", headers=headers).json()

    assert body["total"] == 1
    assert body["items"][0]["added_at"] == first_added_at


def test_finish_report_matches_answers(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()

    for index, question in enumerate(start["questions"]):
        if index < 12:
            _force_correct(client, headers, question["question_id"])
        else:
            _force_wrong(client, headers, question["question_id"])

    report = client.post("/api/quiz/today/finish", headers=headers).json()

    assert report["total_count"] == 20
    assert report["correct_count"] == 12
    assert report["wrong_count"] == 8
    assert report["accuracy"] == round(12 / 20, 4)

    # new_wrong_words = 本轮答错的单词；此前"先答错再答对"的单词仍在错题本（FR-026）
    expected_new = sorted(
        question["word_id"] for question in start["questions"][12:]
    )
    assert sorted(report["new_wrong_words"]) == expected_new
    assert set(expected_new) <= set(wrong_word_ids(client, token))


def test_finished_attempt_rejects_further_answers(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()
    client.post("/api/quiz/today/finish", headers=headers)

    response = client.post(
        "/api/quiz/today/answer",
        headers=headers,
        json={"question_id": start["questions"][0]["question_id"], "choice_index": 0},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "attempt_already_finished"
