"""口令哈希与 JWT 单元测试。"""

from __future__ import annotations

import pytest

from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

pytestmark = pytest.mark.unit


def test_hash_password_is_not_plaintext_and_salted():
    first = hash_password("abc123")
    second = hash_password("abc123")

    assert first != "abc123"
    assert first != second  # 自带随机盐
    assert verify_password("abc123", first)
    assert not verify_password("wrong", first)


def test_jwt_roundtrip():
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_jwt_rejects_tampered_and_garbage():
    token = create_access_token(42)
    assert decode_access_token(token[:-3] + "abc") is None
    assert decode_access_token("not-a-token") is None
    assert decode_access_token("") is None
