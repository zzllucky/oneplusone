"""错题库（永久档案）接口契约测试。"""

from __future__ import annotations

import pytest

from tests.conftest import (
    auth_headers,
    register,
    view_all_today,
)

pytestmark = pytest.mark.contract


def _force_wrong_daily(client, headers, question_id) -> None:
    probe = client.post(
        "/api/quiz/today/answer",
        headers=headers,
        json={"question_id": question_id, "choice_index": 0},
    ).json()
    if not probe["is_correct"]:
        return
    wrong_index = next(index for index in range(4) if index != probe["correct_index"])
    client.post(
        "/api/quiz/today/answer",
        headers=headers,
        json={"question_id": question_id, "choice_index": wrong_index},
    )


def _correct_text(question: dict, item: dict) -> str:
    return (
        item["meaning_zh"]
        if question["prompt"] == item["spelling"]
        else item["spelling"]
    )


def _correct_index(question: dict, item: dict) -> int:
    return question["options"].index(_correct_text(question, item))


def _seed_wrong_words(client, headers, token, count: int = 2) -> list[int]:
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()
    for question in start["questions"][:count]:
        _force_wrong_daily(client, headers, question["question_id"])
    return [question["word_id"] for question in start["questions"][:count]]


def test_empty_archive_list_shape(client):
    token = register(client)["access_token"]

    response = client.get("/api/wrong-words/archive", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["page"] == 1
    assert body["sort"] == "added"


def test_archive_item_shape_after_wrong_answer(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token, count=1)

    body = client.get("/api/wrong-words/archive", headers=headers).json()

    assert body["total"] == 1
    item = body["items"][0]
    for key in ("word_id", "spelling", "meaning_zh", "phrase", "phonetic", "wrong_count"):
        assert key in item
    assert item["word_id"] == seeded[0]
    assert item["wrong_count"] == 1
    # 错题库不记录时间
    assert "added_at" not in item
    assert "last_wrong_at" not in item


def test_archive_start_with_empty_archive_returns_409(client):
    token = register(client)["access_token"]

    response = client.post("/api/quiz/archive/start", headers=auth_headers(token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_archive_words"


def test_archive_questions_only_from_archive(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token, count=2)

    response = client.post("/api/quiz/archive/start", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert sorted(question["word_id"] for question in body["questions"]) == sorted(
        seeded
    )


def test_archive_answer_never_removes(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    _seed_wrong_words(client, headers, token, count=1)

    before = client.get("/api/wrong-words/archive", headers=headers).json()["items"][0]
    assert before["wrong_count"] == 1

    question = client.post("/api/quiz/archive/start", headers=headers).json()[
        "questions"
    ][0]
    correct_index = _correct_index(question, before)
    probe = client.post(
        "/api/quiz/archive/answer",
        headers=headers,
        json={"question_id": question["question_id"], "choice_index": correct_index},
    ).json()

    assert probe["is_correct"] is True
    assert probe["removed_from_wrong_words"] is False
    assert probe["archive_wrong_count"] == 1  # 答对不减次数

    after = client.get("/api/wrong-words/archive", headers=headers).json()
    assert after["total"] == 1
    assert after["items"][0]["wrong_count"] == 1


def test_archive_sort_by_wrong_count(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token, count=2)

    # 让第一个词再错一次：错题库专项练习里故意答错
    items = client.get("/api/wrong-words/archive", headers=headers).json()["items"]
    target = next(item for item in items if item["word_id"] == seeded[0])
    start = client.post("/api/quiz/archive/start", headers=headers).json()
    question = next(
        item for item in start["questions"] if item["word_id"] == seeded[0]
    )
    wrong_index = next(
        index
        for index, option in enumerate(question["options"])
        if option != _correct_text(question, target)
    )
    client.post(
        "/api/quiz/archive/answer",
        headers=headers,
        json={"question_id": question["question_id"], "choice_index": wrong_index},
    )

    body = client.get(
        "/api/wrong-words/archive?sort=count", headers=headers
    ).json()

    assert body["sort"] == "count"
    assert body["items"][0]["word_id"] == seeded[0]
    assert body["items"][0]["wrong_count"] == 2
