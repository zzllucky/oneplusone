"""轮次字段契约测试（T014）：两个端点的新增字段、类型与一致性。"""

from __future__ import annotations

import pytest

from app.models.word import Word
from app.services import round_service
from tests.conftest import auth_headers, register, view_all_today

pytestmark = pytest.mark.contract

LEGACY_HOME_KEYS = {
    "user",
    "daily_goal",
    "today",
    "wrong_word_count",
    "archive_word_count",
}
LEGACY_STUDY_KEYS = {
    "study_date",
    "total_count",
    "viewed_count",
    "all_viewed",
    "quiz_unlocked",
    "library_exhausted",
    "items",
}


def test_home_summary_exposes_round_fields(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)

    body = client.get("/api/home/summary", headers=headers).json()

    assert LEGACY_HOME_KEYS <= set(body), "既有字段必须保留"
    assert body["completed_rounds"] == 0
    assert body["current_round"]["round_no"] == 1
    assert body["current_round"]["total_count"] > 0
    assert isinstance(body["current_round"]["pending_quiz"], bool)


def test_home_summary_round_totals_match_library(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)

    body = client.get("/api/home/summary", headers=headers).json()

    assert body["current_round"]["total_count"] > 0
    assert body["current_round"]["learned_count"] == body["today"]["total_count"]


def test_study_today_exposes_round_field(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)

    body = client.get("/api/study/today", headers=headers).json()

    assert LEGACY_STUDY_KEYS <= set(body), "既有字段必须保留"
    assert body["round"]["round_no"] == 1
    assert body["round"]["learned_count"] == len(body["items"])
    assert body["round"]["total_count"] >= len(body["items"])
    assert isinstance(body["round"]["pending_quiz"], bool)


def test_pending_quiz_true_when_covered_without_quiz(client, db):
    """本轮单词学完但当日测验未完成 → pending_quiz = true，轮数不增加（FR-015）。"""
    payload = register(client)
    headers = auth_headers(payload["access_token"])
    user_id = payload["user"]["id"]

    total = db.query(Word).count()
    ids = round_service.allocate_word_ids(db, user_id, total)
    round_service.advance_cursor(db, user_id, ids)
    view_all_today(client, payload["access_token"])

    home = client.get("/api/home/summary", headers=headers).json()
    study = client.get("/api/study/today", headers=headers).json()

    assert home["current_round"]["pending_quiz"] is True
    assert study["round"]["pending_quiz"] is True
    assert home["completed_rounds"] == 0


def test_round_fields_stable_across_refresh(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)

    first = client.get("/api/home/summary", headers=headers).json()
    second = client.get("/api/home/summary", headers=headers).json()

    assert first["completed_rounds"] == second["completed_rounds"]
    assert first["current_round"] == second["current_round"]
