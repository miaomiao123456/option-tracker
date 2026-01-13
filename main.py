"""
FastAPI 主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.models.database import init_db
from app.routers import summary, fundamental, capital, technical, daily, data_governance
import logging
from pathlib import Path

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
app.include_router(data_governance.router, prefix="/api/v1/data-governance", tags=["数据治理"])

# 新增:智汇期讯专用路由
from app.routers import zhihui
app.include_router(zhihui.router, prefix="/api/v1/zhihui", tags=["智汇期讯"])

# 新增:虚实比模块路由
from app.routers import virtual_real_ratio
app.include_router(virtual_real_ratio.router, prefix="/api/v1/virtual-real-ratio", tags=["虚实比/期限结构"])

# 新增:期限结构模块路由 (支持两种路径以兼容前端不同位置的调用)
from app.routers import term_structure
app.include_router(term_structure.router, prefix="/api/v1/term-structure", tags=["期限结构"])
app.include_router(term_structure.router, prefix="/api/term-structure", tags=["期限结构"])

# 新增:V2分析系统路由
from app.routers import analysis_v2
app.include_router(analysis_v2.router, prefix="/api/v1/analysis-v2", tags=["V2分析系统"])

# 新增:多维度综合分析路由 (Phase 5)
from app.routers import comprehensive
app.include_router(comprehensive.router, prefix="/api/v1/comprehensive", tags=["多维度综合分析"])

# 新增:V3优化分析系统路由
from app.routers import analysis_v3
app.include_router(analysis_v3.router, tags=["V3优化分析"])

# 新增:每日早报路由
from app.routers import daily_report
app.include_router(daily_report.router, tags=["每日早报"])


@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库和定时任务"""
    logger.info("正在初始化数据库...")
    init_db()
    logger.info("数据库初始化完成!")

    # 初始化并启动原有定时任务
    from app.scheduler import init_scheduler, start_scheduler
    init_scheduler()
    start_scheduler()

    # 启动每日早报定时任务
    from app.services.scheduler import start_scheduler as start_report_scheduler
    await start_report_scheduler()
    logger.info("每日早报定时任务已启动 (每天8:30自动生成)")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时停止定时任务"""
    from app.scheduler import stop_scheduler
    stop_scheduler()

    # 停止每日早报定时任务
    from app.services.scheduler import stop_scheduler as stop_report_scheduler
    await stop_report_scheduler()

    logger.info("应用关闭完成")


@app.get("/")
async def root():
    """返回导航首页"""
    index_path = Path(__file__).parent / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "status": "ok",
        "message": "OptionAlpha API is running",
        "version": "1.0.0",
        "frontend": "http://localhost:8000/frontend"
    }


@app.get("/index.html", response_class=HTMLResponse)
async def get_index_html():
    """返回导航首页 - .html扩展名版本"""
    index_path = Path(__file__).parent / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Index page not found</h1>", status_code=404)


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


@app.get("/frontend", response_class=HTMLResponse)
async def get_frontend():
    """返回前端页面"""
    frontend_path = Path(__file__).parent / "frontend.html"
    if frontend_path.exists():
        return FileResponse(
            frontend_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)


@app.get("/frontend.html", response_class=HTMLResponse)
async def get_frontend_html():
    """返回前端页面 - .html扩展名版本"""
    frontend_path = Path(__file__).parent / "frontend.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)


@app.get("/report_detail.html", response_class=HTMLResponse)
async def get_report_detail():
    """返回研报详情页面"""
    report_path = Path(__file__).parent / "report_detail.html"
    if report_path.exists():
        return FileResponse(report_path)
    return HTMLResponse("<h1>Report detail not found</h1>", status_code=404)


@app.get("/v3_analysis.html", response_class=HTMLResponse)
async def get_v3_analysis():
    """返回V3分析页面"""
    v3_path = Path(__file__).parent / "v3_analysis.html"
    if v3_path.exists():
        return FileResponse(
            v3_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>V3 Analysis page not found</h1>", status_code=404)


@app.get("/zhihui.html", response_class=HTMLResponse)
async def get_zhihui():
    """返回智汇期讯页面"""
    zhihui_path = Path(__file__).parent / "zhihui.html"
    if zhihui_path.exists():
        return FileResponse(zhihui_path)
    return HTMLResponse("<h1>Zhihui page not found</h1>", status_code=404)


@app.get("/data_governance.html", response_class=HTMLResponse)
async def get_data_governance_html():
    """返回数据治理页面"""
    dg_path = Path(__file__).parent / "data_governance.html"
    if dg_path.exists():
        return FileResponse(dg_path)
    return HTMLResponse("<h1>Data governance page not found</h1>", status_code=404)


@app.get("/virtual_real_ratio.html", response_class=HTMLResponse)
async def get_virtual_real_ratio_html():
    """返回虚实比分析页面"""
    vr_path = Path(__file__).parent / "virtual_real_ratio.html"
    if vr_path.exists():
        return FileResponse(vr_path)
    return HTMLResponse("<h1>Virtual Real Ratio page not found</h1>", status_code=404)


@app.get("/data-governance", response_class=HTMLResponse)
async def get_data_governance_page():
    """返回数据治理监控页面"""
    governance_path = Path(__file__).parent / "data_governance.html"
    if governance_path.exists():
        return FileResponse(
            governance_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Data Governance page not found</h1>", status_code=404)


@app.get("/analysis-v2", response_class=HTMLResponse)
async def get_analysis_v2_page():
    """返回V2分析总览页面"""
    analysis_path = Path(__file__).parent / "analysis_v2.html"
    if analysis_path.exists():
        return FileResponse(
            analysis_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Analysis V2 page not found</h1>", status_code=404)


@app.get("/zhihui", response_class=HTMLResponse)
async def get_zhihui_page():
    """返回智汇期讯展示页面"""
    zhihui_path = Path(__file__).parent / "zhihui.html"
    if zhihui_path.exists():
        return FileResponse(
            zhihui_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Zhihui page not found</h1>", status_code=404)


@app.get("/report-detail", response_class=HTMLResponse)
async def get_report_detail_page():
    """返回研报详情页面"""
    report_detail_path = Path(__file__).parent / "report_detail.html"
    if report_detail_path.exists():
        return FileResponse(
            report_detail_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Report detail page not found</h1>", status_code=404)


@app.get("/opportunity-radar", response_class=HTMLResponse)
async def get_opportunity_radar_page():
    """返回机会雷达页面"""
    radar_path = Path(__file__).parent / "opportunity_radar.html"
    if radar_path.exists():
        return FileResponse(
            radar_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Opportunity radar page not found</h1>", status_code=404)


@app.get("/opportunity_radar.html", response_class=HTMLResponse)
async def get_opportunity_radar_html():
    """返回机会雷达页面 - .html扩展名版本"""
    radar_path = Path(__file__).parent / "opportunity_radar.html"
    if radar_path.exists():
        return FileResponse(
            radar_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Opportunity radar page not found</h1>", status_code=404)


@app.get("/test_apis.html", response_class=HTMLResponse)
async def get_test_apis_html():
    """返回API测试页面"""
    test_path = Path(__file__).parent / "test_apis.html"
    if test_path.exists():
        return FileResponse(
            test_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Test APIs page not found</h1>", status_code=404)


@app.get("/analysis_v2.html", response_class=HTMLResponse)
async def get_analysis_v2_html():
    """返回V2分析页面 - .html扩展名版本"""
    analysis_path = Path(__file__).parent / "analysis_v2.html"
    if analysis_path.exists():
        return FileResponse(
            analysis_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Analysis V2 page not found</h1>", status_code=404)


@app.get("/capital_flow.html", response_class=HTMLResponse)
async def get_capital_flow_html():
    """返回资金流向分析页面"""
    capital_path = Path(__file__).parent / "capital_flow.html"
    if capital_path.exists():
        return FileResponse(
            capital_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Capital Flow page not found</h1>", status_code=404)


@app.get("/diagnose.html", response_class=HTMLResponse)
async def get_diagnose_html():
    """返回诊断页面"""
    diagnose_path = Path(__file__).parent / "diagnose.html"
    if diagnose_path.exists():
        return FileResponse(
            diagnose_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Diagnose page not found</h1>", status_code=404)


@app.get("/position_analysis.html", response_class=HTMLResponse)
async def get_position_analysis_html():
    """返回持仓分析页面"""
    position_path = Path(__file__).parent / "position_analysis.html"
    if position_path.exists():
        return FileResponse(
            position_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Position Analysis page not found</h1>", status_code=404)


@app.get("/daily_report.html", response_class=HTMLResponse)
async def get_daily_report_html():
    """返回每日早报页面"""
    daily_report_path = Path(__file__).parent / "daily_report.html"
    if daily_report_path.exists():
        return FileResponse(
            daily_report_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Daily Report page not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
