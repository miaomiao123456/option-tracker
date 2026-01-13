"""
每日早报 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional
import json

from app.models.database import get_db
from sqlalchemy import text
from app.services.daily_report_generator import DailyReportGenerator
from app.services.scheduler import trigger_report_now

router = APIRouter(prefix="/api/v1/daily-report", tags=["每日早报"])


@router.get("/latest")
async def get_latest_report():
    """
    获取最新的早报
    """
    db = next(get_db())
    try:
        query = text("""
            SELECT
                report_date,
                generate_time,
                content,
                executive_summary
            FROM daily_reports
            ORDER BY report_date DESC
            LIMIT 1
        """)

        result = db.execute(query).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="暂无早报数据")

        return {
            "success": True,
            "report_date": result.report_date,
            "generate_time": result.generate_time,
            "executive_summary": result.executive_summary,
            "content": json.loads(result.content)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取早报失败: {str(e)}")
    finally:
        db.close()


@router.get("/by-date")
async def get_report_by_date(date: str = Query(..., description="报告日期 YYYY-MM-DD")):
    """
    根据日期获取早报
    """
    db = next(get_db())
    try:
        query = text("""
            SELECT
                report_date,
                generate_time,
                content,
                executive_summary
            FROM daily_reports
            WHERE report_date = :date
        """)

        result = db.execute(query, {"date": date}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"未找到 {date} 的早报")

        return {
            "success": True,
            "report_date": result.report_date,
            "generate_time": result.generate_time,
            "executive_summary": result.executive_summary,
            "content": json.loads(result.content)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取早报失败: {str(e)}")
    finally:
        db.close()


@router.get("/list")
async def get_report_list(days: int = Query(7, description="获取最近N天的报告列表")):
    """
    获取早报列表
    """
    db = next(get_db())
    try:
        query = text("""
            SELECT
                report_date,
                generate_time,
                executive_summary
            FROM daily_reports
            ORDER BY report_date DESC
            LIMIT :limit
        """)

        result = db.execute(query, {"limit": days})
        reports = []

        for row in result:
            reports.append({
                "report_date": row.report_date,
                "generate_time": row.generate_time,
                "executive_summary": row.executive_summary
            })

        return {
            "success": True,
            "count": len(reports),
            "reports": reports
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报告列表失败: {str(e)}")
    finally:
        db.close()


@router.post("/generate")
async def generate_report_now():
    """
    立即生成早报 (手动触发)
    """
    try:
        generator = DailyReportGenerator()
        report = await generator.generate_daily_report()

        return {
            "success": True,
            "message": "早报生成成功",
            "report_date": report['report_date'],
            "generate_time": report['generate_time'],
            "executive_summary": report['executive_summary']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成早报失败: {str(e)}")


@router.get("/preview")
async def preview_report():
    """
    预览早报内容 (不保存到数据库)
    """
    try:
        generator = DailyReportGenerator()

        # 生成报告但不保存
        report_data = {}

        # 获取各项数据
        import asyncio
        tasks = [
            generator._get_market_news(),
            generator._get_top_opportunities(),
            generator._get_research_highlights(),
            generator._get_capital_flow_summary(),
            generator._get_risk_warnings(),
            generator._get_term_structure_signals(),
            generator._get_technical_signals(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        report_data = {
            "report_date": datetime.now().strftime('%Y-%m-%d'),
            "market_news": results[0] if not isinstance(results[0], Exception) else [],
            "top_opportunities": results[1] if not isinstance(results[1], Exception) else [],
            "research_highlights": results[2] if not isinstance(results[2], Exception) else {},
            "capital_flow_summary": results[3] if not isinstance(results[3], Exception) else {},
            "risk_warnings": results[4] if not isinstance(results[4], Exception) else [],
            "term_structure_signals": results[5] if not isinstance(results[5], Exception) else [],
            "technical_signals": results[6] if not isinstance(results[6], Exception) else {},
        }

        # 生成摘要
        report_data["executive_summary"] = generator._generate_executive_summary(report_data)

        return {
            "success": True,
            "preview": report_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")
