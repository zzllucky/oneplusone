"""总结页端到端集成测试（T009 / T017 / T024 / T031）。

真实 SQLite + HTTP 链路，禁用 mock（章程 IV）：行为 → 聚合 → 接口一致。
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from app.models.base import utcnow
from app.models.daily_set import DailySet, DailySetItem
from app.models.quiz import QuizAnswer, QuizAttempt
from app.models.word import Word
from app.services import summary_service
from tests.conftest import auth_headers, login, register

pytestmark = pytest.mark.integration

LOCAL_OFFSET_MINUTES = 8 * 60


def _local_to_utc(day: dt.date, hour: int, minute: int) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(hour, minute)) - dt.timedelta(
        minutes=LOCAL_OFFSET_MINUTES
    )


def _word_ids(db, count: int) -> list[int]:
    return [
        row[0]
        for row in db.execute(select(Word.id).order_by(Word.id).limit(count)).all()
    ]


def _seed_set(db, user_id: int, day: dt.date, total: int, viewed: int = 0) -> None:
    ids = _word_ids(db, max(total, 1))
    daily_set = DailySet(user_id=user_id, study_date=day, created_at=utcnow())
    db.add(daily_set)
    db.flush()
    for index in range(total):
        db.add(
            DailySetItem(
                daily_set_id=daily_set.id,
                word_id=ids[index],
                order_index=index + 1,
                viewed_at=utcnow() if index < viewed else None,
            )
        )
    db.commit()


def _seed_attempt(
    db,
    user_id: int,
    kind: str,
    *,
    study_date: dt.date | None = None,
    total: int = 10,
    correct: int = 8,
    answers: list[tuple[bool, dt.datetime]] | None = None,
) -> int:
    attempt = QuizAttempt(
        user_id=user_id,
        kind=kind,
        study_date=study_date,
        started_at=utcnow(),
        finished_at=utcnow(),
        total_count=total,
        correct_count=correct,
        wrong_count=total - correct,
    )
    db.add(attempt)
    db.flush()
    ids = _word_ids(db, max(len(answers or []), 1))
    for index, (is_correct, answered_at) in enumerate(answers or []):
        db.add(
            QuizAnswer(
                attempt_id=attempt.id,
                word_id=ids[index],
                question_type="en2zh",
                choice_index=0 if is_correct else 1,
                is_correct=is_correct,
                answered_at=answered_at,
            )
        )
    db.commit()
    return attempt.id


def _study_all_today(client, token: str) -> int:
    """浏览当日全部单词，返回浏览数量。"""
    headers = auth_headers(token)
    items = client.get("/api/study/today", headers=headers).json()["items"]
    for item in items:
        response = client.post(
            f"/api/study/today/items/{item['word_id']}/view", headers=headers
        )
        assert response.status_code == 200, response.text
    return len(items)


def _finish_today_quiz(client, token: str) -> None:
    headers = auth_headers(token)
    started = client.post("/api/quiz/today/start", headers=headers)
    assert started.status_code == 200, started.text
    for question in started.json()["questions"]:
        answered = client.post(
            "/api/quiz/today/answer",
            json={"question_id": question["question_id"], "choice_index": 0},
            headers=headers,
        )
        assert answered.status_code == 200, answered.text
    finished = client.post("/api/quiz/today/finish", headers=headers)
    assert finished.status_code == 200, finished.text


def _server_today(client, token: str) -> dt.date:
    body = client.get("/api/study/today", headers=auth_headers(token)).json()
    return dt.date.fromisoformat(body["study_date"])


def test_month_colors_today_and_history_days(client, db):
    """学过 = 深绿；只打开过 = 浅绿；无记录 = 灰色（US1 / FR-019）。"""
    payload = register(client)
    token, user_id = payload["access_token"], payload["user"]["id"]
    headers = auth_headers(token)

    today = _server_today(client, token)
    learned = _study_all_today(client, token)
    _finish_today_quiz(client, token)

    yesterday = today - dt.timedelta(days=1)
    _seed_set(db, user_id, yesterday, total=5, viewed=0)

    this_month = client.get(
        f"/api/summary/month?month={today.strftime('%Y-%m')}", headers=headers
    ).json()
    yesterday_month = client.get(
        f"/api/summary/month?month={yesterday.strftime('%Y-%m')}", headers=headers
    ).json()

    today_cell = next(item for item in this_month["days"] if item["date"] == today.isoformat())
    assert today_cell["level"] == "deep"
    assert today_cell["learned_count"] == learned

    yesterday_cell = next(
        item for item in yesterday_month["days"] if item["date"] == yesterday.isoformat()
    )
    assert yesterday_cell["level"] == "light"
    assert yesterday_cell["learned_count"] == 0

    empty_day = today - dt.timedelta(days=2)
    empty_month = client.get(
        f"/api/summary/month?month={empty_day.strftime('%Y-%m')}", headers=headers
    ).json()
    empty_cell = next(
        item for item in empty_month["days"] if item["date"] == empty_day.isoformat()
    )
    assert empty_cell["level"] == "gray"


def test_day_summary_matches_actual_behavior(client, db):
    """四项明细与实际行为一致，多轮专项练习累加而非覆盖（US2 / FR-012）。"""
    payload = register(client)
    token, user_id = payload["access_token"], payload["user"]["id"]
    headers = auth_headers(token)

    today = _server_today(client, token)
    learned = _study_all_today(client, token)
    _finish_today_quiz(client, token)

    # 两类专项练习各若干轮，作答时刻均落在今天
    for _round in range(2):
        _seed_attempt(
            db,
            user_id,
            "review",
            answers=[
                (True, _local_to_utc(today, 20, _round)),
                (False, _local_to_utc(today, 20, _round + 30)),
            ],
        )
    _seed_attempt(
        db,
        user_id,
        "archive",
        answers=[(True, _local_to_utc(today, 21, 0))],
    )

    body = client.get(
        f"/api/summary/day?date={today.isoformat()}", headers=headers
    ).json()

    assert body["has_record"] is True
    assert body["learned_count"] == learned
    attempt_total = db.scalar(
        select(QuizAttempt.total_count).where(
            QuizAttempt.user_id == user_id, QuizAttempt.kind == "daily"
        )
    )
    assert body["quiz"]["completed"] is True
    assert body["quiz"]["answered"] == attempt_total
    assert body["review_practice"]["rounds"] == 2, "多轮必须累加"
    assert body["review_practice"]["answered"] == 4
    assert body["review_practice"]["correct"] == 2
    assert body["review_practice"]["wrong"] == 2
    assert body["archive_practice"]["rounds"] == 1
    assert body["archive_practice"]["answered"] == 1


def test_history_identical_after_relogin(client, db):
    """换 token（重新登录 / 换设备）后历史着色与明细完全一致（US5 / FR-014）。"""
    payload = register(client, login_name="stu01")
    user_id = payload["user"]["id"]
    token = payload["access_token"]
    headers = auth_headers(token)

    last_month_day = dt.date.today().replace(day=1) - dt.timedelta(days=1)
    for offset in range(3):
        day = last_month_day - dt.timedelta(days=offset)
        _seed_set(db, user_id, day, total=6, viewed=4)
    _seed_attempt(
        db, user_id, "daily", study_date=last_month_day, total=10, correct=6
    )
    month_key = last_month_day.strftime("%Y-%m")

    first_month = client.get(f"/api/summary/month?month={month_key}", headers=headers).json()
    first_day = client.get(
        f"/api/summary/day?date={last_month_day.isoformat()}", headers=headers
    ).json()

    new_token = login(client, "stu01")["access_token"]
    second_month = client.get(
        f"/api/summary/month?month={month_key}", headers=auth_headers(new_token)
    ).json()
    second_day = client.get(
        f"/api/summary/day?date={last_month_day.isoformat()}",
        headers=auth_headers(new_token),
    ).json()

    assert first_month == second_month
    assert first_day == second_day
    assert second_day["learned_count"] == 4
    assert second_day["quiz"]["completed"] is True


def test_accounts_cannot_see_each_other(client, db):
    """跨账号隔离：每人只看到自己的汇总（FR-016 / SC-007）。"""
    first = register(client, login_name="stuA")
    second = register(client, login_name="stuB")
    first_token, first_id = first["access_token"], first["user"]["id"]
    second_token, second_id = second["access_token"], second["user"]["id"]

    # 不经过 /study/today（它会为账号生成今日集合），直接取服务端当日
    today = summary_service.today_date()
    yesterday = today - dt.timedelta(days=1)
    _seed_set(db, first_id, today, total=5, viewed=3)
    _seed_set(db, second_id, yesterday, total=5, viewed=5)

    first_month = client.get(
        f"/api/summary/month?month={today.strftime('%Y-%m')}",
        headers=auth_headers(first_token),
    ).json()
    second_month = client.get(
        f"/api/summary/month?month={today.strftime('%Y-%m')}",
        headers=auth_headers(second_token),
    ).json()

    def level_of(body: dict, day: dt.date) -> str:
        cell = next(
            (item for item in body["days"] if item["date"] == day.isoformat()), None
        )
        return cell["level"] if cell else "absent"

    expected_second = 5 if yesterday.strftime("%Y-%m") == today.strftime("%Y-%m") else 0

    assert level_of(first_month, today) == "deep"
    assert level_of(second_month, today) == "gray", "B 不得看到 A 的学习记录"
    assert first_month["month_total"]["learned_words"] == 3, "A 的月度总计只含自己的数据"
    assert second_month["month_total"]["learned_words"] == expected_second
    assert first_month["days"] != second_month["days"], "两个账号的日历不得相同"
