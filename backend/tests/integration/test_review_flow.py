"""错题专项练习全链路：题目来源、答对移除（唯一路径）、答错保留、报告。"""

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
        "/api/quiz/review/answer",
        headers=headers,
        json={"question_id": question_id, "choice_index": choice_index},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _force_wrong(client, headers, question_id) -> dict:
    probe = _answer(client, headers, question_id, 0)
    if not probe["is_correct"]:
        return probe
    wrong_index = next(index for index in range(4) if index != probe["correct_index"])
    return _answer(client, headers, question_id, wrong_index)


def _force_correct(client, headers, question_id) -> dict:
    probe = _answer(client, headers, question_id, 0)
    if probe["is_correct"]:
        return probe
    return _answer(client, headers, question_id, probe["correct_index"])


def _clear_from_wrong_book(client, headers, question_id) -> dict:
    """连续两次提交正确答案（中间不能答错，否则 streak 归零）→ 移出错题本。"""
    probe = _force_correct(client, headers, question_id)
    return _answer(client, headers, question_id, probe["correct_index"])


def _definitely_wrong_index(question: dict, item: dict) -> int:
    """依据题目类型挑一个必错选项：无需"先探测再改答"，避免误删错题记录。"""
    correct_text = (
        item["meaning_zh"] if question["prompt"] == item["spelling"] else item["spelling"]
    )
    for index, option in enumerate(question["options"]):
        if option != correct_text:
            return index
    raise AssertionError("选项与正确答案完全相同，题目异常")


def _seed_wrong_words(client, headers, token, count: int = 3) -> list[int]:
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()
    for question in start["questions"][:count]:
        _force_wrong_daily(client, headers, question["question_id"])
    return wrong_word_ids(client, token)


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


def test_review_questions_come_only_from_wrong_book(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token)

    start = client.post("/api/quiz/review/start", headers=headers).json()
    assert sorted(q["word_id"] for q in start["questions"]) == sorted(seeded)


def test_correct_answer_removes_wrong_word_after_streak(client):
    """答对 1 次仅累计 streak，连续答对 2 次才移出错题本。"""
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token)

    start = client.post("/api/quiz/review/start", headers=headers).json()
    target = start["questions"][0]

    first = _force_correct(client, headers, target["question_id"])
    assert first["is_correct"] is True
    assert first["removed_from_wrong_words"] is False
    assert first["correct_streak"] == 1
    assert target["word_id"] in wrong_word_ids(client, token)

    second = _answer(client, headers, target["question_id"], first["correct_index"])
    assert second["removed_from_wrong_words"] is True

    remaining = wrong_word_ids(client, token)
    assert target["word_id"] not in remaining
    assert len(remaining) == len(seeded) - 1


def test_wrong_answer_resets_streak(client):
    """答对一次后答错 → 连续答对归零，需重新累计两次才移出。"""
    token = register(client)["access_token"]
    headers = auth_headers(token)
    _seed_wrong_words(client, headers, token, count=1)

    start = client.post("/api/quiz/review/start", headers=headers).json()
    target = start["questions"][0]

    first = _force_correct(client, headers, target["question_id"])
    assert first["correct_streak"] == 1

    _force_wrong(client, headers, target["question_id"])
    assert wrong_word_ids(client, token) == [target["word_id"]]

    again = _answer(client, headers, target["question_id"], first["correct_index"])
    assert again["removed_from_wrong_words"] is False  # 归零后只累计到 1
    assert again["correct_streak"] == 1


def test_wrong_answer_keeps_record_and_added_at(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    _seed_wrong_words(client, headers, token)

    before = client.get("/api/wrong-words", headers=headers).json()["items"]
    target = client.post("/api/quiz/review/start", headers=headers).json()["questions"][0]
    before_item = next(item for item in before if item["word_id"] == target["word_id"])

    result = _answer(
        client, headers, target["question_id"], _definitely_wrong_index(target, before_item)
    )
    assert result["is_correct"] is False

    after = client.get("/api/wrong-words", headers=headers).json()["items"]
    after_item = next(item for item in after if item["word_id"] == target["word_id"])
    assert after_item["added_at"] == before_item["added_at"]


def test_re_answer_wrong_after_correct_restores_record(client):
    """同一题在一轮内先答对（移除）后改答为错 → 重新入本，加入时间为本次答错。"""
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token, count=1)

    start = client.post("/api/quiz/review/start", headers=headers).json()
    target = start["questions"][0]

    first = _force_correct(client, headers, target["question_id"])  # 第一次：仅累计
    correct = _answer(
        client, headers, target["question_id"], first["correct_index"]
    )  # 第二次：移出
    assert correct["removed_from_wrong_words"] is True
    assert wrong_word_ids(client, token) == []

    restored = _force_wrong(client, headers, target["question_id"])
    assert restored["is_correct"] is False
    assert restored["added_back_to_wrong_words"] is True
    assert wrong_word_ids(client, token) == seeded


def test_review_finish_report_remaining_count(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    _seed_wrong_words(client, headers, token, count=3)

    start = client.post("/api/quiz/review/start", headers=headers).json()
    for question in start["questions"][:2]:
        _clear_from_wrong_book(client, headers, question["question_id"])
    _force_wrong(client, headers, start["questions"][2]["question_id"])

    report = client.post("/api/quiz/review/finish", headers=headers).json()

    assert report["total_count"] == 3
    assert report["correct_count"] == 2
    assert report["wrong_count"] == 1
    assert report["remaining_wrong_count"] == 1
    assert len(wrong_word_ids(client, token)) == 1
