"""Alembic 迁移环境。

数据库地址优先取自环境变量 ``DB_PATH``（与运行时一致），缺失时回退到 alembic.ini。
"""

from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db import Base
from app.models import *  # noqa: F401,F403  注册全部模型以便 autogenerate 可见

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_db_path = os.environ.get("DB_PATH")
if _db_path:
    # 统一使用 POSIX 分隔符，保证与运行时 engine 指向同一个文件
    config.set_main_option("sqlalchemy.url", f"sqlite:///{Path(_db_path).as_posix()}")

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
