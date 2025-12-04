"""数据库连接管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.base import Base
from config.settings import get_settings

settings = get_settings()

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库,创建所有表"""
    # 导入所有模型以确保它们被注册到Base.metadata
    from app.models import models  # 导入原有业务模型
    from app.models import data_governance  # 导入数据治理模型

    Base.metadata.create_all(bind=engine)
    print("数据库表创建成功!")


def get_db() -> Session:
    """获取数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
