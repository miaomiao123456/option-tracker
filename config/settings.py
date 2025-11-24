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

    # API Keys
    GEMINI_API_KEY: str
    GEMINI_BASE_URL: str = "https://www.apillm.online/v1"

    # 项目配置
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
