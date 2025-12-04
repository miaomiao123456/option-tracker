"""配置管理"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 数据库
    DATABASE_URL: str = "sqlite:///./option_tracker.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 账号配置
    JYK_USER: str
    JYK_PASS: str
    ZHIHUI_USER: str = ""
    ZHIHUI_PASS: str = ""
    ZHIHUI_AUTH_TOKEN: str = ""  # 智汇期讯 Authorization Token

    # API Keys
    GEMINI_API_KEY: str
    GEMINI_BASE_URL: str = "https://www.apillm.online/v1"

    # 飞书告警配置
    FEISHU_WEBHOOK: str = ""  # 飞书机器人 Webhook URL

    # 项目配置
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
