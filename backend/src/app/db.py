"""SQLAlchemy engine / session（SQLite + WAL）。

测试需要为每个用例切换到独立数据库文件，因此 engine 与 session factory
通过 :func:`init_engine` 重建；``get_db`` 在调用时读取模块级变量，保证
依赖注入拿到的是当前 engine 的会话。
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """声明式基类，所有模型继承它。"""


def _sqlite_url(db_path: str) -> str:
    return f"sqlite:///{Path(db_path).as_posix()}"


def _create_engine(url: str) -> Engine:
    engine = create_engine(url, connect_args={"check_same_thread": False}, future=True)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine: Engine | None = None
SessionLocal: sessionmaker | None = None


def init_engine(db_path: str | None = None) -> Engine:
    """（重新）初始化 engine 与 session factory。"""
    global engine, SessionLocal

    path = db_path or os.environ.get("DB_PATH") or settings.db_path
    if path != ":memory:":
        directory = Path(path).parent
        if str(directory) and not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)

    engine = _create_engine(_sqlite_url(path))
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine


def get_db() -> Iterator[Session]:
    assert SessionLocal is not None, "数据库未初始化，请先调用 init_engine()"
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


init_engine()
