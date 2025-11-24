"""
基本面模块 API
提供智汇期讯、方期看盘等基本面数据
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.database import get_db
from app.models.models import FundamentalReport
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime

router = APIRouter()


class ReportItem(BaseModel):
    """研报数据"""
    id: int
    variety_code: str
    source: str
    report_type: str
    sentiment: str
    content_summary: str
    publish_time: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/{variety_code}", response_model=List[ReportItem])
async def get_fundamental_data(
        variety_code: str,
        source: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """
    获取品种的基本面数据
    """
    query = db.query(FundamentalReport).filter(
        FundamentalReport.comm_code == variety_code
    )

    if source:
        query = query.filter(FundamentalReport.source == source)

    reports = query.order_by(desc(FundamentalReport.publish_time)).limit(50).all()

    if not reports:
        raise HTTPException(status_code=404, detail=f"未找到品种 {variety_code} 的基本面数据")

    return reports


@router.get("/{variety_code}/reports")
async def get_variety_reports(
        variety_code: str,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """
    获取品种的研报列表
    """
    reports = db.query(FundamentalReport).filter(
        FundamentalReport.comm_code == variety_code
    ).order_by(desc(FundamentalReport.publish_time)).limit(limit).all()

    if not reports:
        return {"reports": []}

    # 按情绪分组统计
    bull_count = sum(1 for r in reports if r.sentiment == 'bull')
    bear_count = sum(1 for r in reports if r.sentiment == 'bear')
    neutral_count = sum(1 for r in reports if r.sentiment == 'neutral')

    return {
        "variety_code": variety_code,
        "total_reports": len(reports),
        "sentiment_distribution": {
            "bull": bull_count,
            "bear": bear_count,
            "neutral": neutral_count
        },
        "reports": [
            {
                "source": r.source,
                "type": r.report_type,
                "sentiment": r.sentiment,
                "summary": r.content_summary,
                "publish_time": r.publish_time
            }
            for r in reports
        ]
    }


@router.get("/{variety_code}/sentiment")
async def get_sentiment_analysis(
        variety_code: str,
        days: int = 7,
        db: Session = Depends(get_db)
):
    """
    获取品种的情绪分析（最近N天）
    """
    from datetime import timedelta

    start_date = date.today() - timedelta(days=days)

    reports = db.query(FundamentalReport).filter(
        FundamentalReport.comm_code == variety_code,
        FundamentalReport.publish_time >= start_date
    ).all()

    if not reports:
        return {
            "variety_code": variety_code,
            "days": days,
            "sentiment": "neutral",
            "confidence": 0
        }

    # 计算情绪倾向
    bull_count = sum(1 for r in reports if r.sentiment == 'bull')
    bear_count = sum(1 for r in reports if r.sentiment == 'bear')

    total = len(reports)
    bull_ratio = bull_count / total if total > 0 else 0
    bear_ratio = bear_count / total if total > 0 else 0

    if bull_ratio > 0.6:
        sentiment = "bull"
        confidence = bull_ratio
    elif bear_ratio > 0.6:
        sentiment = "bear"
        confidence = bear_ratio
    else:
        sentiment = "neutral"
        confidence = 0.5

    return {
        "variety_code": variety_code,
        "days": days,
        "sentiment": sentiment,
        "confidence": round(confidence * 100, 2),
        "bull_ratio": round(bull_ratio * 100, 2),
        "bear_ratio": round(bear_ratio * 100, 2),
        "sample_size": total
    }
