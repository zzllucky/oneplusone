"""测试基座：每个用例独立 SQLite 文件 + 执行 alembic upgrade head（含词表 seed）。"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = BACKEND_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

_TMP_ROOT = Path(tempfile.gettempdir()) / "word-study-tests"
_TMP_ROOT.mkdir(parents=True, exist_ok=True)

# 必须在导入 app 之前设置，避免创建默认 data/app.db
os.environ["DB_PATH"] = str(_TMP_ROOT / "bootstrap.db")
os.environ["PRONOUNCE_CACHE_DIR"] = str(_TMP_ROOT / "pronounce-cache")
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-only-0123456789")

from app import db as db_module  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


def _alembic_upgrade(db_path: Path) -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    os.environ["DB_PATH"] = str(db_path)
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def _no_server_tts(monkeypatch):
    """默认关闭服务端 TTS，避免测试联网；需要验证 TTS 的用例自行替换。"""
    from app.services import pronounce_service

    monkeypatch.setattr(pronounce_service, "synthesize_edge", lambda text: None)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def engine(db_path: Path):
    """初始化独立数据库并执行全部迁移（001 建表 + 002 词表 seed）。"""
    db_module.init_engine(str(db_path))
    _alembic_upgrade(db_path)
    return db_path


@pytest.fixture
def db(engine):
    session = db_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine):
    with TestClient(fastapi_app) as test_client:
        yield test_client


def register(
    client: TestClient,
    *,
    login_name: str = "stu01",
    nickname: str = "小明",
    password: str = "abc123",
) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "login_name": login_name,
            "nickname": nickname,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, login_name: str = "stu01", password: str = "abc123") -> dict:
    response = client.post(
        "/api/auth/login", json={"login_name": login_name, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def user(client: TestClient) -> dict:
    """注册并登录，返回 {token, user}。"""
    payload = register(client)
    return {"token": payload["access_token"], "user": payload["user"]}


def today_word_ids(client: TestClient, token: str) -> list[int]:
    response = client.get("/api/study/today", headers=auth_headers(token))
    assert response.status_code == 200, response.text
    return [item["word_id"] for item in response.json()["items"]]


def view_all_today(client: TestClient, token: str) -> None:
    for word_id in today_word_ids(client, token):
        response = client.post(
            f"/api/study/today/items/{word_id}/view", headers=auth_headers(token)
        )
        assert response.status_code == 200, response.text


def wrong_word_ids(client: TestClient, token: str) -> list[int]:
    response = client.get("/api/wrong-words", headers=auth_headers(token))
    assert response.status_code == 200, response.text
    return [item["word_id"] for item in response.json()["items"]]
