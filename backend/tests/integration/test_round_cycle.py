"""词库循环学习全链路（T010 / T013 / T026）：真实 SQLite + HTTP。

场景 A —— 词库耗尽后次日仍有词可学
场景 B —— 新一轮按词库原顺序、每词一次
场景 E —— 跨轮过渡日不混轮
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.models.word import Word
from app.services import round_service, study_service
from tests.conftest import auth_headers, register, view_all_today

pytestmark = pytest.mark.integration


def _push_cursor_to_remaining(db, user_id: int, remaining: int) -> None:
    """把当前轮游标推进到"只剩 remaining 个单词"（造数，仅供测试）。"""
    total = db.query(Word).count()
    ids = round_service.allocate_word_ids(db, user_id, total - remaining)
    round_service.advance_cursor(db, user_id, ids)


def _shift_today(monkeypatch, days: int) -> None:
    base = study_service.today_date()

    monkeypatch.setattr(
        study_service, "today_date", lambda now=None: base + dt.timedelta(days=days)
    )


def _answer(client, headers, question_id, choice_index) -> dict:
    response = client.post(
        "/api/quiz/today/answer",
        headers=headers,
        json={"question_id": question_id, "choice_index": choice_index},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _force_correct(client, headers, question_id) -> None:
    probe = _answer(client, headers, question_id, 0)
    if not probe["is_correct"]:
        _answer(client, headers, question_id, probe["correct_index"])


def _force_wrong(client, headers, question_id) -> None:
    probe = _answer(client, headers, question_id, 0)
    if probe["is_correct"]:
        wrong_index = next(
            index for index in range(4) if index != probe["correct_index"]
        )
        _answer(client, headers, question_id, wrong_index)


def _finish_quiz(client, headers) -> None:
    response = client.post("/api/quiz/today/finish", headers=headers)
    assert response.status_code == 200, response.text


def test_scenario_a_library_exhausted_no_longer_blocks(client, db, monkeypatch):
    """场景 A：词库学完后，次日仍有词可学，首页不再是 0 / 0（SC-001 / SC-002）。"""
    payload = register(client)
    token = payload["access_token"]
    headers = auth_headers(token)
    user_id = payload["user"]["id"]

    _push_cursor_to_remaining(db, user_id, remaining=2)
    view_all_today(client, token)

    start = client.post("/api/quiz/today/start", headers=headers).json()
    for question in start["questions"]:
        _force_correct(client, headers, question["question_id"])
    _finish_quiz(client, headers)

    _shift_today(monkeypatch, 1)

    study = client.get("/api/study/today", headers=headers).json()
    assert study["items"], "词库学完后次日必须仍有单词可学"

    home = client.get("/api/home/summary", headers=headers).json()
    assert home["today"]["total_count"] > 0


def test_scenario_b_new_round_follows_library_order(client, db, monkeypatch):
    """场景 B：新一轮从词库首个单词开始、按原顺序推进、一轮内无重复（FR-012 / SC-004）。"""
    payload = register(client)
    token = payload["access_token"]
    headers = auth_headers(token)
    user_id = payload["user"]["id"]

    _push_cursor_to_remaining(db, user_id, remaining=1)
    view_all_today(client, token)

    _shift_today(monkeypatch, 1)
    first_day = [item["word_id"] for item in
                 client.get("/api/study/today", headers=headers).json()["items"]]
    head_ids = [row[0] for row in db.query(Word.id).order_by(Word.id).limit(len(first_day))]
    assert first_day == head_ids, "新一轮必须从词库首个单词开始"

    _shift_today(monkeypatch, 2)
    second_day = [item["word_id"] for item in
                  client.get("/api/study/today", headers=headers).json()["items"]]
    assert not set(first_day) & set(second_day), "一轮内不重复分配"
    assert second_day == sorted(second_day)
    assert min(second_day) == max(first_day) + 1, "按词库原顺序连续推进"


def test_scenario_e_transition_day_does_not_mix_rounds(client, db):
    """场景 E：跨轮过渡日只分配本轮剩余单词，不从新一轮借词（FR-009）。"""
    payload = register(client)
    token = payload["access_token"]
    headers = auth_headers(token)
    user_id = payload["user"]["id"]

    _push_cursor_to_remaining(db, user_id, remaining=3)
    study = client.get("/api/study/today", headers=headers).json()

    assert len(study["items"]) == 3
    assert study["library_exhausted"] is True


def test_scenario_d_round_settled_next_day_even_from_home(client, db, monkeypatch):
    """场景 D：轮末只浏览未测验 → 次日补记为已完成；**先看首页也要一致**（FR-014 / SC-006）。"""
    from app.models.quiz import QuizAttempt

    payload = register(client)
    token = payload["access_token"]
    headers = auth_headers(token)
    user_id = payload["user"]["id"]

    _push_cursor_to_remaining(db, user_id, remaining=2)
    view_all_today(client, token)
    assert db.query(QuizAttempt).count() == 0  # 从未做过测验

    _shift_today(monkeypatch, 1)

    home = client.get("/api/home/summary", headers=headers).json()
    assert home["completed_rounds"] == 1, "补记必须在首页读取入口就已生效"

    study = client.get("/api/study/today", headers=headers).json()
    assert study["items"], "补记后应能立即开始新一轮"
    assert study["round"]["round_no"] == 2

    # 刷新与重新登录后完全一致
    again = client.get("/api/home/summary", headers=headers).json()
    relogin = auth_headers(
        client.post(
            "/api/auth/login", json={"login_name": "stu01", "password": "abc123"}
        ).json()["access_token"]
    )
    assert again["completed_rounds"] == 1
    assert client.get("/api/home/summary", headers=relogin).json()[
        "completed_rounds"
    ] == 1
    assert db.query(QuizAttempt).count() == 0  # 补记不伪造测验成绩


def test_scenario_f_history_preserved_across_rounds(client, db, monkeypatch):
    """场景 F：跨轮不清空历史 —— 每日记录、测验结果、错题本、错题库均不变（FR-008）。"""
    from app.models.daily_set import DailySet, DailySetItem
    from app.models.quiz import QuizAttempt
    from app.models.wrong_word import WrongWord
    from app.models.wrong_word_archive import WrongWordArchive

    payload = register(client)
    token = payload["access_token"]
    headers = auth_headers(token)
    user_id = payload["user"]["id"]

    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()
    for question in start["questions"][:2]:
        _force_wrong(client, headers, question["question_id"])
    client.post("/api/quiz/today/finish", headers=headers)
    assert db.query(WrongWord).count() > 0, "前置条件：跨轮前已有错题数据"

    def snapshot() -> dict:
        return {
            "daily_sets": db.query(DailySet).count(),
            "daily_set_items": db.query(DailySetItem).count(),
            "quiz_attempts": db.query(QuizAttempt).count(),
            "wrong_words": db.query(WrongWord).count(),
            "archive": db.query(WrongWordArchive).count(),
        }

    before = snapshot()

    total = db.query(Word).count()
    ids = round_service.allocate_word_ids(db, user_id, total)
    round_service.advance_cursor(db, user_id, ids)

    first_day_set = db.query(DailySet).order_by(DailySet.id).first()

    _shift_today(monkeypatch, 1)
    client.get("/api/study/today", headers=headers)  # 触发跨轮

    after = snapshot()
    assert all(after[key] >= before[key] for key in before), "跨轮不得减少任何历史数据"
    # 错题本 / 错题库 / 测验结果条数与内容不受跨轮影响
    assert after["wrong_words"] == before["wrong_words"]
    assert after["archive"] == before["archive"]
    assert after["quiz_attempts"] == before["quiz_attempts"]
    # 历史每日记录仍然可查
    assert (
        db.query(DailySet).filter(DailySet.id == first_day_set.id).count() == 1
    )
