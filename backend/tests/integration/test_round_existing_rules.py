"""新一轮沿用既有学习与测验规则（T024）：目标生效、测验解锁、答错入错题本 / 错题库。"""

from __future__ import annotations

import datetime as dt

import pytest

from app.models.word import Word
from app.services import round_service, study_service
from tests.conftest import auth_headers, register, today_word_ids, view_all_today

pytestmark = pytest.mark.integration


def _enter_new_round(client, db, monkeypatch, user_id: int, token: str) -> None:
    """把账号推进到"新一轮首日"：本轮只剩 1 个单词 → 学完 → 次日开启新一轮。"""
    total = db.query(Word).count()
    ids = round_service.allocate_word_ids(db, user_id, total - 1)
    round_service.advance_cursor(db, user_id, ids)
    view_all_today(client, token)

    base = study_service.today_date()
    monkeypatch.setattr(
        study_service, "today_date", lambda now=None: base + dt.timedelta(days=1)
    )


def test_goal_change_reallocates_in_new_round(client, db, monkeypatch):
    """未浏览任何单词时改目标 → 当日集合立即重算（与首轮同规则）。"""
    payload = register(client)
    token = payload["access_token"]
    headers = auth_headers(token)
    _enter_new_round(client, db, monkeypatch, payload["user"]["id"], token)

    before = today_word_ids(client, token)
    client.put("/api/settings", headers=headers, json={"daily_goal": 30})
    after = today_word_ids(client, token)

    assert len(after) == 30
    assert set(after) >= set(before), "按 id 升序分配，原集合是新集合的前缀"


def test_goal_change_keeps_set_after_viewing_in_new_round(client, db, monkeypatch):
    """已浏览 ≥ 1 个单词后改目标 → 当日集合不变（与首轮同规则）。"""
    payload = register(client)
    token = payload["access_token"]
    headers = auth_headers(token)
    _enter_new_round(client, db, monkeypatch, payload["user"]["id"], token)

    before = today_word_ids(client, token)
    client.post(f"/api/study/today/items/{before[0]}/view", headers=headers)
    client.put("/api/settings", headers=headers, json={"daily_goal": 30})

    assert today_word_ids(client, token) == before


def test_quiz_still_locked_before_all_viewed_in_new_round(client, db, monkeypatch):
    """未完成全部浏览 → 今日测验仍 409 quiz_locked（与首轮同规则）。"""
    payload = register(client)
    token = payload["access_token"]
    headers = auth_headers(token)
    _enter_new_round(client, db, monkeypatch, payload["user"]["id"], token)

    response = client.post("/api/quiz/today/start", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "quiz_locked"


def test_wrong_answer_still_fills_wrong_books_in_new_round(client, db, monkeypatch):
    """新一轮测验答错 → 仍进入错题本与错题库（规则不变）。"""
    payload = register(client)
    token = payload["access_token"]
    headers = auth_headers(token)
    _enter_new_round(client, db, monkeypatch, payload["user"]["id"], token)

    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()

    def _force_wrong(question_id: int) -> None:
        probe = client.post(
            "/api/quiz/today/answer",
            headers=headers,
            json={"question_id": question_id, "choice_index": 0},
        ).json()
        if probe["is_correct"]:
            wrong_index = next(i for i in range(4) if i != probe["correct_index"])
            client.post(
                "/api/quiz/today/answer",
                headers=headers,
                json={"question_id": question_id, "choice_index": wrong_index},
            )

    targets = start["questions"][:2]
    for question in targets:
        _force_wrong(question["question_id"])

    stored = client.get("/api/wrong-words", headers=headers).json()["items"]
    home = client.get("/api/home/summary", headers=headers).json()

    assert {item["word_id"] for item in stored} >= {
        question["word_id"] for question in targets
    }
    assert home["archive_word_count"] >= len(targets)
