"""错题库全链路：永久留档、只累加、错题本清空后仍在。"""

from __future__ import annotations

import pytest

from tests.conftest import (
    auth_headers,
    register,
    view_all_today,
    wrong_word_ids,
)

pytestmark = pytest.mark.integration


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


def _seed_wrong_words(client, headers, token, count: int = 2) -> list[int]:
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()
    for question in start["questions"][:count]:
        _force_wrong_daily(client, headers, question["question_id"])
    return wrong_word_ids(client, token)


def _archive_counts(client, headers) -> dict[int, int]:
    body = client.get("/api/wrong-words/archive?page=1&page_size=100", headers=headers)
    return {item["word_id"]: item["wrong_count"] for item in body.json()["items"]}


def _correct_index(question: dict, item: dict) -> int:
    correct_text = (
        item["meaning_zh"] if question["prompt"] == item["spelling"] else item["spelling"]
    )
    return question["options"].index(correct_text)


def _clear_wrong_book(client, headers, item: dict) -> None:
    """直接用正确选项连续答对两次（不产生额外错误记录）→ 移出错题本。"""
    start = client.post("/api/quiz/review/start", headers=headers).json()
    question = start["questions"][0]
    index = _correct_index(question, item)
    for _ in range(2):
        response = client.post(
            "/api/quiz/review/answer",
            headers=headers,
            json={"question_id": question["question_id"], "choice_index": index},
        )
        assert response.status_code == 200, response.text


def _definitely_wrong_index(question: dict, item: dict) -> int:
    correct_text = (
        item["meaning_zh"] if question["prompt"] == item["spelling"] else item["spelling"]
    )
    for index, option in enumerate(question["options"]):
        if option != correct_text:
            return index
    raise AssertionError("选项与正确答案完全相同，题目异常")


def test_wrong_answer_feeds_archive(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token, count=2)

    counts = _archive_counts(client, headers)
    assert set(counts) == set(seeded)
    assert all(count == 1 for count in counts.values())


def test_archive_survives_wrong_book_clearing(client):
    """错题本被清空（连续答对达标）后，错题库仍保留全部记录。"""
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token, count=1)

    item = client.get("/api/wrong-words", headers=headers).json()["items"][0]
    _clear_wrong_book(client, headers, item)

    assert wrong_word_ids(client, token) == []
    assert _archive_counts(client, headers) == {seeded[0]: 1}


def test_archive_quiz_wrong_answer_accumulates_and_returns_to_book(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token, count=1)

    # 先清空错题本，验证错题库练习答错能把单词放回待复习队列
    item = client.get("/api/wrong-words", headers=headers).json()["items"][0]
    _clear_wrong_book(client, headers, item)
    client.post("/api/quiz/review/finish", headers=headers)
    assert wrong_word_ids(client, token) == []

    archive_item = client.get("/api/wrong-words/archive", headers=headers).json()[
        "items"
    ][0]
    archive_start = client.post("/api/quiz/archive/start", headers=headers).json()
    archive_question = archive_start["questions"][0]
    result = client.post(
        "/api/quiz/archive/answer",
        headers=headers,
        json={
            "question_id": archive_question["question_id"],
            "choice_index": _definitely_wrong_index(archive_question, archive_item),
        },
    ).json()

    assert result["is_correct"] is False
    assert result["added_to_wrong_words"] is True
    assert result["archive_wrong_count"] == 2
    assert wrong_word_ids(client, token) == seeded


def test_archive_finish_report_keeps_total(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    _seed_wrong_words(client, headers, token, count=2)

    start = client.post("/api/quiz/archive/start", headers=headers).json()
    for question in start["questions"]:
        probe = client.post(
            "/api/quiz/archive/answer",
            headers=headers,
            json={"question_id": question["question_id"], "choice_index": 0},
        ).json()
        if not probe["is_correct"]:
            client.post(
                "/api/quiz/archive/answer",
                headers=headers,
                json={
                    "question_id": question["question_id"],
                    "choice_index": probe["correct_index"],
                },
            )

    report = client.post("/api/quiz/archive/finish", headers=headers).json()

    assert report["total_count"] == 2
    assert report["correct_count"] == 2
    assert report["archive_total"] == 2  # 全对也不减少
    assert _archive_counts(client, headers) != {}
