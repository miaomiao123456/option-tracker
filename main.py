"""
FastAPI 主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.database import init_db
from app.routers import summary, fundamental, capital, technical, daily
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="期权交易跟踪器 API",
    description="OptionAlpha - 期货期权交易四维分析系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(summary.router, prefix="/api/v1/summary", tags=["总览"])
app.include_router(fundamental.router, prefix="/api/v1/fundamental", tags=["基本面"])
app.include_router(capital.router, prefix="/api/v1/capital", tags=["资金面"])
app.include_router(technical.router, prefix="/api/v1/technical", tags=["技术面"])
app.include_router(daily.router, prefix="/api/v1/daily", tags=["日报"])


@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库和定时任务"""
    logger.info("正在初始化数据库...")
    init_db()
    logger.info("数据库初始化完成!")

    # 初始化并启动定时任务
    from app.scheduler import init_scheduler, start_scheduler
    init_scheduler()
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时停止定时任务"""
    from app.scheduler import stop_scheduler
    stop_scheduler()
    logger.info("应用关闭完成")


@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "message": "OptionAlpha API is running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
