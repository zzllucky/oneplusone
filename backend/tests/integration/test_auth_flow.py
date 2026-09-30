"""注册 → 登出 → 登录 → 访问受限接口的完整链路。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, register

pytestmark = pytest.mark.integration


def test_register_login_and_protected_access(client):
    payload = register(client, login_name="stu01", nickname="小明")
    token = payload["access_token"]

    me = client.get("/api/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["nickname"] == "小明"

    # 登出 = 前端丢弃 token；服务端无状态，旧 token 仍可用是预期行为
    relogin = client.post(
        "/api/auth/login", json={"login_name": "stu01", "password": "abc123"}
    )
    assert relogin.status_code == 200
    assert relogin.json()["user"]["id"] == payload["user"]["id"]

    # 未携带 token 访问受限接口
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/settings").status_code == 401


def test_login_works_with_any_case_of_login_name(client):
    register(client, login_name="Stu01", nickname="小明")

    for name in ("stu01", "STU01", "Stu01"):
        response = client.post(
            "/api/auth/login", json={"login_name": name, "password": "abc123"}
        )
        assert response.status_code == 200, name


def test_password_is_never_returned_or_stored_in_plain_text(client, db):
    register(client, login_name="stu01", nickname="小明", password="secret123")

    from app.models.user import User

    user = db.query(User).filter(User.login_name == "stu01").one()
    assert user.password_hash != "secret123"
    assert "secret123" not in user.password_hash

    body = client.post(
        "/api/auth/login", json={"login_name": "stu01", "password": "secret123"}
    ).json()
    assert "password" not in body
    assert "password_hash" not in body
