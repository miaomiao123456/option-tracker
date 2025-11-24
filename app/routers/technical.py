"""
技术面模块 API
提供波动率、期限结构等技术指标数据
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.database import get_db
from app.models.models import TechnicalIndicator
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

router = APIRouter()


class TechIndicator(BaseModel):
    """技术指标数据"""
    comm_code: str
    iv_rank: Optional[float]
    term_structure: Optional[str]
    pcr_ratio: Optional[float]
    record_time: datetime

    class Config:
        from_attributes = True


@router.get("/{variety_code}/indicators")
async def get_technical_indicators(
        variety_code: str,
        db: Session = Depends(get_db)
):
    """
    获取品种的技术指标
    """
    # 获取最新一条记录
    indicator = db.query(TechnicalIndicator).filter(
        TechnicalIndicator.comm_code == variety_code
    ).order_by(desc(TechnicalIndicator.record_time)).first()

    if not indicator:
        raise HTTPException(status_code=404, detail=f"未找到品种 {variety_code} 的技术指标数据")

    return {
        "variety_code": variety_code,
        "indicators": {
            "iv_rank": indicator.iv_rank,
            "term_structure": indicator.term_structure,
            "pcr_ratio": indicator.pcr_ratio
        },
        "record_time": indicator.record_time
    }


@router.get("/{variety_code}/structure")
async def get_term_structure(
        variety_code: str,
        db: Session = Depends(get_db)
):
    """
    获取品种的期限结构
    """
    indicator = db.query(TechnicalIndicator).filter(
        TechnicalIndicator.comm_code == variety_code
    ).order_by(desc(TechnicalIndicator.record_time)).first()

    if not indicator:
        raise HTTPException(status_code=404, detail=f"未找到数据")

    structure = indicator.term_structure or "unknown"

    # 判断结构类型
    if "contango" in structure.lower() or "升水" in structure:
        structure_type = "contango"
        description = "远月升水结构，通常利于做空"
    elif "back" in structure.lower() or "贴水" in structure:
        structure_type = "back"
        description = "近月贴水结构，通常利于做多"
    else:
        structure_type = "flat"
        description = "平水结构"

    return {
        "variety_code": variety_code,
        "term_structure": {
            "type": structure_type,
            "raw_value": structure,
            "description": description
        }
    }


@router.get("/{variety_code}/iv-history")
async def get_iv_history(
        variety_code: str,
        days: int = Query(30, ge=1, le=90),
        db: Session = Depends(get_db)
):
    """
    获取品种的历史波动率
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    indicators = db.query(TechnicalIndicator).filter(
        TechnicalIndicator.comm_code == variety_code,
        TechnicalIndicator.record_time.between(start_time, end_time)
    ).order_by(TechnicalIndicator.record_time).all()

    if not indicators:
        return {
            "variety_code": variety_code,
            "iv_history": []
        }

    return {
        "variety_code": variety_code,
        "days": days,
        "iv_history": [
            {
                "time": ind.record_time.isoformat(),
                "iv_rank": ind.iv_rank,
                "pcr_ratio": ind.pcr_ratio
            }
            for ind in indicators
        ]
    }


@router.get("/structures/significant")
async def get_significant_structures(
        db: Session = Depends(get_db)
):
    """
    获取所有明显期限结构的品种
    (contango 或 back 结构明显的品种)
    """
    # 获取所有最新的技术指标
    from sqlalchemy import func

    subq = db.query(
        TechnicalIndicator.comm_code,
        func.max(TechnicalIndicator.record_time).label('max_time')
    ).group_by(TechnicalIndicator.comm_code).subquery()

    latest_indicators = db.query(TechnicalIndicator).join(
        subq,
        (TechnicalIndicator.comm_code == subq.c.comm_code) &
        (TechnicalIndicator.record_time == subq.c.max_time)
    ).all()

    contango_varieties = []
    back_varieties = []

    for ind in latest_indicators:
        structure = (ind.term_structure or "").lower()

        if "contango" in structure or "升水" in structure:
            contango_varieties.append({
                "variety_code": ind.comm_code,
                "structure": ind.term_structure,
                "iv_rank": ind.iv_rank
            })
        elif "back" in structure or "贴水" in structure:
            back_varieties.append({
                "variety_code": ind.comm_code,
                "structure": ind.term_structure,
                "iv_rank": ind.iv_rank
            })

    return {
        "contango_varieties": contango_varieties,
        "back_varieties": back_varieties,
        "total_count": len(contango_varieties) + len(back_varieties)
    }
