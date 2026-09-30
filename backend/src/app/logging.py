"""结构化日志配置。

安全约束：任何日志调用 MUST NOT 携带明文口令、口令哈希或 JWT。
"""

from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # 第三方库降噪
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
