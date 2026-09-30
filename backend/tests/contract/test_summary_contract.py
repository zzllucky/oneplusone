"""总结接口契约测试（T008 / T016 / T020）：字段集合、参数校验、无记录日期。"""

from __future__ import annotations

import calendar
import datetime as dt

import pytest

from tests.conftest import auth_headers, register

pytestmark = pytest.mark.contract

# 在线时长已整体移除：响应中不得出现任何时长类字段
DURATION_KEYS = {
    "online_minutes",
    "online_duration",
    "study_minutes",
    "duration",
    "active_minutes",
    "time_spent",
}


def _month_length(value: str) -> int:
    year, month = int(value[:4]), int(value[5:7])
    return calendar.monthrange(year, month)[1]


def test_month_summary_exposes_contract_fields(client):
    token = register(client)["access_token"]

    body = client.get("/api/summary/month", headers=auth_headers(token)).json()

    assert set(body) == {"month", "today", "days", "month_total", "streak_days"}
    today = dt.date.fromisoformat(body["today"])
    assert body["month"] == today.strftime("%Y-%m"), "缺省应为当前月"
    assert len(body["days"]) == _month_length(body["month"])
    dates = [item["date"] for item in body["days"]]
    assert dates == sorted(dates), "日期必须升序"
    for item in body["days"]:
        assert item["level"] in ("gray", "light", "deep")
        assert 0 <= item["shade"] <= 3
        assert isinstance(item["learned_count"], int)
        if item["level"] != "deep":
            assert item["shade"] == 0
    assert set(body["month_total"]) == {
        "learned_words",
        "quiz",
        "review_practice",
        "archive_practice",
        "active_days",
    }
    assert isinstance(body["streak_days"], int)


def test_month_summary_rejects_invalid_month(client):
    token = register(client)["access_token"]

    response = client.get("/api/summary/month?month=2026/09", headers=auth_headers(token))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_month"


def test_day_summary_fields_and_no_duration(client):
    token = register(client)["access_token"]

    body = client.get(
        f"/api/summary/day?date={dt.date.today().isoformat()}",
        headers=auth_headers(token),
    ).json()

    assert set(body) == {
        "date",
        "has_record",
        "learned_count",
        "quiz",
        "review_practice",
        "archive_practice",
    }
    assert set(body["quiz"]) == {
        "completed",
        "rounds",
        "answered",
        "correct",
        "wrong",
    }
    for key in ("review_practice", "archive_practice"):
        assert set(body[key]) == {"rounds", "answered", "correct", "wrong"}
    assert not DURATION_KEYS & set(body), "不得返回任何在线时长字段"


def test_day_summary_rejects_invalid_date(client):
    token = register(client)["access_token"]

    response = client.get(
        "/api/summary/day?date=2026-09-32", headers=auth_headers(token)
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_date"


def test_day_without_record_returns_200_with_false(client):
    """灰色日 / 未来日期 → 200 + has_record=false，不是 404（US3 / FR-015）。"""
    token = register(client)["access_token"]
    headers = auth_headers(token)

    past = client.get("/api/summary/day?date=2000-01-01", headers=headers)
    future = client.get("/api/summary/day?date=2099-12-31", headers=headers)

    assert past.status_code == 200
    assert future.status_code == 200
    for body in (past.json(), future.json()):
        assert body["has_record"] is False
        assert body["learned_count"] == 0
        assert body["quiz"]["completed"] is False
        assert body["quiz"]["answered"] == 0


def test_summary_endpoints_require_auth(client):
    assert client.get("/api/summary/month").status_code == 401
    assert client.get("/api/summary/day?date=2026-09-01").status_code == 401
