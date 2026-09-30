"""应用配置：全部来自环境变量 / .env。"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 安全：JWT 密钥由环境注入，禁止入库与写日志
    jwt_secret: str = "dev-only-secret-change-me"
    jwt_expire_days: int = 7

    # 存储
    db_path: str = "data/app.db"

    # 每日目标默认值
    daily_goal_default: int = 20

    # 发音代理（服务端代理第三方公共发音接口）
    pronounce_upstream_url: str = (
        "https://dict.youdao.com/dictvoice?audio={word}&type=1"
    )
    pronounce_timeout_seconds: float = 2.0
    pronounce_cache_dir: str = "data/cache/pronounce"

    # 服务端 TTS（edge-tts）：整句例句也能发音，不依赖浏览器语音合成
    tts_voice: str = "en-US-AriaNeural"
    tts_rate: str = "-15%"
    tts_timeout_seconds: float = 8.0

    # "当日" 边界所用时区（服务端统一计算，避免按设备时区漂移）
    timezone: str = "Asia/Shanghai"

    # 前端构建产物目录（存在时由后端静态托管）
    static_dir: str = "../frontend/dist"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
