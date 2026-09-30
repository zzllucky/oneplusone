"""错题持久性：跨日、重新登录、学习新词、今日测验答对 —— 数量一律不变。"""

from __future__ import annotations

import datetime as dt

import pytest

from app.models.daily_set import DailySet
from tests.conftest import (
    auth_headers,
    register,
    today_word_ids,
    view_all_today,
    wrong_word_ids,
)

pytestmark = pytest.mark.integration


def _force_wrong(client, headers, question_id) -> None:
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


def _seed_wrong_words(client, headers, token, count: int = 3) -> list[int]:
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()
    for question in start["questions"][:count]:
        _force_wrong(client, headers, question["question_id"])
    return wrong_word_ids(client, token)


def test_relogin_does_not_clear_wrong_words(client):
    token = register(client)["access_token"]
    seeded = _seed_wrong_words(client, auth_headers(token), token)

    new_token = client.post(
        "/api/auth/login", json={"login_name": "stu01", "password": "abc123"}
    ).json()["access_token"]

    assert wrong_word_ids(client, new_token) == seeded


def test_new_day_does_not_clear_wrong_words(client, db):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token)

    # 把当日集合标记为昨天，模拟跨日
    daily_set = db.query(DailySet).one()
    daily_set.study_date = daily_set.study_date - dt.timedelta(days=1)
    db.commit()

    new_ids = today_word_ids(client, token)
    assert not set(new_ids) & set(seeded)  # 新的一天分配新单词
    assert wrong_word_ids(client, token) == seeded  # 错题一个不少


def test_learning_new_words_does_not_clear_wrong_words(client, db):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token)

    daily_set = db.query(DailySet).one()
    daily_set.study_date = daily_set.study_date - dt.timedelta(days=1)
    db.commit()

    view_all_today(client, token)  # 学习新单词
    assert wrong_word_ids(client, token) == seeded


def test_daily_quiz_correct_answer_does_not_clear_wrong_words(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token)

    start = client.post("/api/quiz/today/start", headers=headers).json()
    target = next(
        question
        for question in start["questions"]
        if question["word_id"] in seeded
    )
    probe = client.post(
        "/api/quiz/today/answer",
        headers=headers,
        json={"question_id": target["question_id"], "choice_index": 0},
    ).json()
    if not probe["is_correct"]:
        client.post(
            "/api/quiz/today/answer",
            headers=headers,
            json={
                "question_id": target["question_id"],
                "choice_index": probe["correct_index"],
            },
        )

    assert wrong_word_ids(client, token) == seeded


def test_changing_goal_does_not_clear_wrong_words(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    seeded = _seed_wrong_words(client, headers, token)

    client.put("/api/settings", headers=headers, json={"daily_goal": 50})
    assert wrong_word_ids(client, token) == seeded
