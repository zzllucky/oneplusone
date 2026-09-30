"""账号接口契约测试（contracts/api.md —— Auth 段）。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers

pytestmark = pytest.mark.contract


def test_register_returns_201_with_expected_fields(client):
    response = client.post(
        "/api/auth/register",
        json={"login_name": "stu01", "nickname": "小明", "password": "abc123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert set(body["user"]) == {"id", "login_name", "nickname"}
    assert "password" not in body and "password_hash" not in body


@pytest.mark.parametrize(
    "login_name", ["ab", "a" * 21, "中文名", "has space", "bad-name!"]
)
def test_invalid_login_name_returns_422(client, login_name):
    response = client.post(
        "/api/auth/register",
        json={"login_name": login_name, "nickname": "小明", "password": "abc123"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_login_name"


@pytest.mark.parametrize("nickname", ["", "   ", "x" * 25])
def test_invalid_nickname_returns_422(client, nickname):
    response = client.post(
        "/api/auth/register",
        json={"login_name": "stu01", "nickname": nickname, "password": "abc123"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_nickname"


def test_weak_password_returns_422(client):
    response = client.post(
        "/api/auth/register",
        json={"login_name": "stu01", "nickname": "小明", "password": "12345"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "weak_password"


def test_duplicate_login_name_ignoring_case_returns_409(client):
    client.post(
        "/api/auth/register",
        json={"login_name": "stu01", "nickname": "小明", "password": "abc123"},
    )
    response = client.post(
        "/api/auth/register",
        json={"login_name": "STU01", "nickname": "小红", "password": "abc123"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "login_name_taken"


def test_duplicate_nickname_is_allowed(client):
    first = client.post(
        "/api/auth/register",
        json={"login_name": "stu01", "nickname": "小明", "password": "abc123"},
    )
    second = client.post(
        "/api/auth/register",
        json={"login_name": "stu02", "nickname": "小明", "password": "abc123"},
    )

    assert first.status_code == 201
    assert second.status_code == 201


def test_login_returns_bearer_token(client):
    client.post(
        "/api/auth/register",
        json={"login_name": "stu01", "nickname": "小明", "password": "abc123"},
    )
    response = client.post(
        "/api/auth/login", json={"login_name": "stu01", "password": "abc123"}
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


@pytest.mark.parametrize(
    "login_name,password", [("stu01", "wrong-pwd"), ("nobody", "abc123")]
)
def test_login_failure_is_uniform_401(client, login_name, password):
    client.post(
        "/api/auth/register",
        json={"login_name": "stu01", "nickname": "小明", "password": "abc123"},
    )
    response = client.post(
        "/api/auth/login", json={"login_name": login_name, "password": password}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_matches_login_name_case_insensitively(client):
    client.post(
        "/api/auth/register",
        json={"login_name": "Stu01", "nickname": "小明", "password": "abc123"},
    )

    assert (
        client.post(
            "/api/auth/login", json={"login_name": "stu01", "password": "abc123"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login", json={"login_name": "STU01", "password": "abc123"}
        ).status_code
        == 200
    )


def test_me_returns_daily_goal(client):
    token = client.post(
        "/api/auth/register",
        json={"login_name": "stu01", "nickname": "小明", "password": "abc123"},
    ).json()["access_token"]

    response = client.get("/api/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["daily_goal"] == 20
    assert body["login_name"] == "stu01"


def test_protected_endpoints_require_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/settings").status_code == 401
    assert client.get("/api/study/today").status_code == 401
    assert client.get("/api/wrong-words").status_code == 401
    assert client.get("/api/home/summary").status_code == 401

    response = client.get("/api/auth/me", headers=auth_headers("garbage-token"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
