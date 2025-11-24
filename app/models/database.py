"""数据库连接管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import get_settings
from app.models.models import Base

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
    Base.metadata.create_all(bind=engine)
    print("数据库表创建成功!")


def get_db() -> Session:
    """获取数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
