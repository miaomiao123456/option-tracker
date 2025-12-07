"""
基本面模块 API
提供智汇期讯、方期看盘等基本面数据
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.database import get_db
from app.models.models import FundamentalReport, Commodity, MarketFullView
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import date, datetime
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

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


class ZhihuiSentiment(BaseModel):
    """智汇期讯市场情绪数据"""
    variety_code: str
    variety_name: str
    excessive_ratio: float  # 看多占比%
    neutral_ratio: float    # 中性占比%
    empty_ratio: float      # 看空占比%
    excessive_num: int      # 看多数量
    neutral_num: int        # 中性数量
    empty_num: int          # 看空数量
    sum: int                # 总数
    more_port: str          # 主流观点
    more_rate: float        # 主流观点比例
    main_sentiment: str     # 情绪标签
    record_time: str


@router.get("/zhihui/market-sentiment", response_model=List[ZhihuiSentiment])
async def get_zhihui_market_sentiment(
        target_date: Optional[str] = None,
        sentiment_filter: Optional[str] = None
):
    """
    获取智汇期讯市场情绪数据（多空全景）

    Args:
        target_date: 目标日期 (格式: YYYYMMDD)，默认为今天
        sentiment_filter: 情绪过滤 ('bull', 'bear', 'neutral')，默认返回全部
    """
    if target_date is None:
        target_date = date.today().strftime('%Y%m%d')

    # 读取智汇期讯数据文件
    data_dir = Path(__file__).parent.parent.parent / "智汇期讯" / "data"
    filename = f"{target_date}_多空全景.json"
    filepath = data_dir / filename

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=f"未找到日期 {target_date} 的智汇期讯数据"
        )

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 如果有情绪过滤
        if sentiment_filter:
            data = [item for item in data if item['main_sentiment'] == sentiment_filter]

        return data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"读取数据失败: {str(e)}"
        )


@router.get("/zhihui/latest-date")
async def get_zhihui_latest_trading_date(db: Session = Depends(get_db)):
    """
    获取数据库中最新的交易日期
    用于前端日期选择器默认值,非交易日时自动回退到最近交易日
    """
    try:
        # 从MarketFullView表查询最新日期
        latest_record = db.query(MarketFullView.record_date).order_by(
            desc(MarketFullView.record_date)
        ).first()

        if latest_record:
            return {
                "success": True,
                "latest_date": latest_record[0].strftime('%Y-%m-%d')
            }
        else:
            # 如果没有数据,返回当前日期
            logger.warning("数据库中没有交易数据,返回当前日期")
            return {
                "success": True,
                "latest_date": date.today().strftime('%Y-%m-%d')
            }
    except Exception as e:
        logger.error(f"获取最新交易日期失败: {e}")
        return {
            "success": False,
            "latest_date": date.today().strftime('%Y-%m-%d')
        }


@router.get("/zhihui/sentiment-stats")
async def get_zhihui_sentiment_stats(target_date: Optional[str] = None):
    """
    获取智汇期讯市场情绪统计

    返回看多、看空、中性的品种数量和比例
    """
    if target_date is None:
        target_date = date.today().strftime('%Y%m%d')

    data_dir = Path(__file__).parent.parent.parent / "智汇期讯" / "data"
    filename = f"{target_date}_多空全景.json"
    filepath = data_dir / filename

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=f"未找到日期 {target_date} 的智汇期讯数据"
        )

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total = len(data)
        bull_count = sum(1 for item in data if item['main_sentiment'] == 'bull')
        bear_count = sum(1 for item in data if item['main_sentiment'] == 'bear')
        neutral_count = sum(1 for item in data if item['main_sentiment'] == 'neutral')

        # 找出最看多和最看空的品种
        sorted_by_bull = sorted(data, key=lambda x: x['excessive_ratio'], reverse=True)
        sorted_by_bear = sorted(data, key=lambda x: x['empty_ratio'], reverse=True)

        return {
            "date": target_date,
            "total_varieties": total,
            "sentiment_distribution": {
                "bull": {"count": bull_count, "ratio": round(bull_count / total * 100, 2) if total > 0 else 0},
                "bear": {"count": bear_count, "ratio": round(bear_count / total * 100, 2) if total > 0 else 0},
                "neutral": {"count": neutral_count, "ratio": round(neutral_count / total * 100, 2) if total > 0 else 0}
            },
            "top_bullish": sorted_by_bull[:5],
            "top_bearish": sorted_by_bear[:5]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"读取数据失败: {str(e)}"
        )


@router.get("/commodities/mapping", response_model=Dict[str, str])
async def get_commodity_mapping(db: Session = Depends(get_db)):
    """
    获取品种代码到名称的映射

    返回: {"AG": "沪银", "CU": "沪铜", ...}
    """
    commodities = db.query(Commodity).all()
    return {c.code: c.name for c in commodities}
