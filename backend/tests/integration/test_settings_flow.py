"""每日目标设置：持久化、次日生效、首页摘要联动。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, register, today_word_ids

pytestmark = pytest.mark.integration


def test_goal_persists_across_sessions(client):
    token = register(client)["access_token"]
    client.put("/api/settings", headers=auth_headers(token), json={"daily_goal": 30})

    # 重新登录
    new_token = client.post(
        "/api/auth/login", json={"login_name": "stu01", "password": "abc123"}
    ).json()["access_token"]

    assert (
        client.get("/api/settings", headers=auth_headers(new_token)).json()["daily_goal"]
        == 30
    )
    assert client.get("/api/auth/me", headers=auth_headers(new_token)).json()[
        "daily_goal"
    ] == 30


def test_goal_change_reallocates_when_today_not_started(client):
    """FR-010：当日尚未浏览任何单词 → 改目标立即重算当日集合。"""
    token = register(client)["access_token"]
    headers = auth_headers(token)
    before = today_word_ids(client, token)
    assert len(before) == 20

    client.put("/api/settings", headers=headers, json={"daily_goal": 30})
    after = today_word_ids(client, token)

    assert len(after) == 30
    assert set(after) >= set(before)  # 按 id 升序分配，原集合是前缀

    client.put("/api/settings", headers=headers, json={"daily_goal": 5})
    assert len(today_word_ids(client, token)) == 5


def test_goal_change_keeps_today_set_after_viewing(client):
    """FR-010：已浏览 ≥ 1 个单词 → 当日集合与进度不变，次日生效。"""
    token = register(client)["access_token"]
    headers = auth_headers(token)
    before = today_word_ids(client, token)

    assert client.post(
        f"/api/study/today/items/{before[0]}/view", headers=headers
    ).status_code == 200

    client.put("/api/settings", headers=headers, json={"daily_goal": 30})
    after = today_word_ids(client, token)

    assert after == before
    assert client.get("/api/study/today", headers=headers).json()[
        "viewed_count"
    ] == 1


def test_home_summary_reflects_goal_and_progress(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)

    body = client.get("/api/home/summary", headers=headers).json()
    assert body["daily_goal"] == 20
    assert body["today"]["total_count"] == 20
    assert body["today"]["viewed_count"] == 0
    assert body["wrong_word_count"] == 0
    assert body["user"]["nickname"] == "小明"

    client.put("/api/settings", headers=headers, json={"daily_goal": 5})
    assert client.get("/api/home/summary", headers=headers).json()["daily_goal"] == 5
