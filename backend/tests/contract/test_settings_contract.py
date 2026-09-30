"""设置接口契约测试（contracts/api.md —— Settings 段）。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, register

pytestmark = pytest.mark.contract


def test_get_settings_returns_default_goal(client):
    token = register(client)["access_token"]

    response = client.get("/api/settings", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["daily_goal"] == 20
    assert "updated_at" in body


def test_put_settings_updates_goal(client):
    token = register(client)["access_token"]

    response = client.put(
        "/api/settings", headers=auth_headers(token), json={"daily_goal": 30}
    )

    assert response.status_code == 200
    assert response.json()["daily_goal"] == 30
    assert (
        client.get("/api/settings", headers=auth_headers(token)).json()["daily_goal"]
        == 30
    )


@pytest.mark.parametrize("daily_goal", [0, -1, 201, 300])
def test_out_of_range_goal_returns_422(client, daily_goal):
    token = register(client)["access_token"]

    response = client.put(
        "/api/settings", headers=auth_headers(token), json={"daily_goal": daily_goal}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "goal_out_of_range"


def test_settings_require_authentication(client):
    assert client.get("/api/settings").status_code == 401
    assert client.put("/api/settings", json={"daily_goal": 10}).status_code == 401
