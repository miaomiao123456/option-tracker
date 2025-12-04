"""
总览模块 API
提供品种总览、多空排行、搜索等功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.database import get_db
from app.models.models import MarketAnalysisSummary, Commodity, DirectionEnum
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

router = APIRouter()


# Pydantic 响应模型
class VarietySummary(BaseModel):
    """品种总览数据"""
    code: str
    name: str
    fundamental_score: int
    capital_score: int
    technical_score: int
    message_score: int
    total_direction: str
    main_reason: str
    date: date

    class Config:
        from_attributes = True


class TopMovers(BaseModel):
    """多空排行榜"""
    long: List[VarietySummary]
    short: List[VarietySummary]


@router.get("/overview", response_model=List[VarietySummary])
async def get_overview(
        target_date: Optional[date] = None,
        db: Session = Depends(get_db)
):
    """
    获取所有品种的四维总览
    """
    if target_date is None:
        target_date = date.today()

    summaries = db.query(MarketAnalysisSummary).filter(
        MarketAnalysisSummary.date == target_date
    ).all()

    if not summaries:
        raise HTTPException(status_code=404, detail=f"未找到 {target_date} 的数据")

    return [
        VarietySummary(
            code=s.comm_code,
            name=s.comm_code,  # 需要关联 Commodity 表获取名称
            fundamental_score=s.fundamental_score,
            capital_score=s.capital_score,
            technical_score=s.technical_score,
            message_score=s.message_score,
            total_direction=s.total_direction.value if s.total_direction else "中性",
            main_reason=s.main_reason or "",
            date=s.date
        )
        for s in summaries
    ]


@router.get("/top-movers", response_model=TopMovers)
async def get_top_movers(
        limit: int = Query(3, ge=1, le=10),
        target_date: Optional[date] = None,
        db: Session = Depends(get_db)
):
    """
    获取多空前N名品种
    """
    if target_date is None:
        target_date = date.today()

    # 计算总分 = 各维度加权和
    # 这里简单相加，实际可以加权
    total_score_expr = (
            MarketAnalysisSummary.fundamental_score +
            MarketAnalysisSummary.capital_score +
            MarketAnalysisSummary.technical_score +
            MarketAnalysisSummary.message_score
    ).label('total_score')

    # 做多品种（总分最高，且大于0）
    long_list = db.query(MarketAnalysisSummary).filter(
        MarketAnalysisSummary.date == target_date,
        total_score_expr > 0
    ).order_by(desc(total_score_expr)).limit(limit).all()

    # 做空品种（总分最低，且小于0）
    short_list = db.query(MarketAnalysisSummary).filter(
        MarketAnalysisSummary.date == target_date,
        total_score_expr < 0
    ).order_by(total_score_expr).limit(limit).all()

    return TopMovers(
        long=[
            VarietySummary(
                code=s.comm_code,
                name=s.comm_code,
                fundamental_score=s.fundamental_score,
                capital_score=s.capital_score,
                technical_score=s.technical_score,
                message_score=s.message_score,
                total_direction=s.total_direction.value,
                main_reason=s.main_reason or "",
                date=s.date
            )
            for s in long_list
        ],
        short=[
            VarietySummary(
                code=s.comm_code,
                name=s.comm_code,
                fundamental_score=s.fundamental_score,
                capital_score=s.capital_score,
                technical_score=s.technical_score,
                message_score=s.message_score,
                total_direction=s.total_direction.value,
                main_reason=s.main_reason or "",
                date=s.date
            )
            for s in short_list
        ]
    )


@router.get("/search")
async def search_variety(
        q: str = Query(..., min_length=1, description="品种代码或名称"),
        db: Session = Depends(get_db)
):
    """
    搜索品种
    """
    # 先从品种基础表搜索
    commodities = db.query(Commodity).filter(
        (Commodity.code.like(f"%{q}%")) |
        (Commodity.name.like(f"%{q}%"))
    ).all()

    if not commodities:
        raise HTTPException(status_code=404, detail=f"未找到品种: {q}")

    return {
        "results": [
            {
                "code": c.code,
                "name": c.name,
                "exchange": c.exchange,
                "category": c.category
            }
            for c in commodities
        ]
    }


@router.get("/{variety_code}/summary")
async def get_variety_summary(
        variety_code: str,
        target_date: Optional[date] = None,
        db: Session = Depends(get_db)
):
    """
    获取单个品种的四维总览
    """
    if target_date is None:
        target_date = date.today()

    summary = db.query(MarketAnalysisSummary).filter(
        MarketAnalysisSummary.comm_code == variety_code,
        MarketAnalysisSummary.date == target_date
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail=f"未找到品种 {variety_code} 在 {target_date} 的数据")

    return {
        "code": summary.comm_code,
        "date": summary.date,
        "scores": {
            "fundamental": summary.fundamental_score,
            "capital": summary.capital_score,
            "technical": summary.technical_score,
            "message": summary.message_score
        },
        "direction": summary.total_direction.value if summary.total_direction else "中性",
        "reason": summary.main_reason or ""
    }
