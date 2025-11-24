"""
日报模块 API
提供交易蓝图、策略生成等功能
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.database import get_db
from app.models.models import DailyBlueprint
from typing import Optional
from datetime import date
import json

router = APIRouter()


@router.get("/blueprint")
async def get_daily_blueprint(
        target_date: Optional[date] = None,
        db: Session = Depends(get_db)
):
    """
    获取每日交易蓝图
    """
    if target_date is None:
        target_date = date.today()

    blueprint = db.query(DailyBlueprint).filter(
        DailyBlueprint.record_date == target_date
    ).first()

    if not blueprint:
        raise HTTPException(status_code=404, detail=f"未找到 {target_date} 的交易蓝图")

    strategies = []
    if blueprint.parsed_strategies:
        try:
            strategies = json.loads(blueprint.parsed_strategies)
        except:
            pass

    return {
        "date": str(blueprint.record_date),
        "image_url": blueprint.image_url,
        "local_path": blueprint.local_path,
        "strategies": strategies
    }


@router.post("/generate-strategy")
async def generate_strategy(
        variety_code: str,
        db: Session = Depends(get_db)
):
    """
    根据四维数据自动生成交易策略
    """
    from app.models.models import MarketAnalysisSummary, InstitutionalPosition

    target_date = date.today()

    # 获取四维数据
    summary = db.query(MarketAnalysisSummary).filter(
        MarketAnalysisSummary.comm_code == variety_code,
        MarketAnalysisSummary.date == target_date
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail=f"未找到品种 {variety_code} 的数据")

    # 获取席位数据
    positions = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == target_date
    ).all()

    # 生成策略逻辑
    strategy = _generate_strategy_logic(summary, positions)

    return strategy


def _generate_strategy_logic(summary, positions):
    """
    策略生成逻辑
    """
    total_score = (
            summary.fundamental_score +
            summary.capital_score +
            summary.technical_score +
            summary.message_score
    )

    # 判断方向
    if total_score > 10:
        direction = "做多"
        confidence = "高"
    elif total_score > 5:
        direction = "做多"
        confidence = "中"
    elif total_score < -10:
        direction = "做空"
        confidence = "高"
    elif total_score < -5:
        direction = "做空"
        confidence = "中"
    else:
        direction = "观望"
        confidence = "低"

    # 分析席位数据
    if positions:
        institution_net = sum(p.net_position for p in positions[:10])  # 前10为机构
        retail_net = sum(p.net_position for p in positions[10:])  # 其他为散户

        position_signal = ""
        if institution_net > 0 and retail_net < 0:
            position_signal = "机构做多，散户做空（利于做多）"
        elif institution_net < 0 and retail_net > 0:
            position_signal = "机构做空，散户做多（利于做空）"
        else:
            position_signal = "机构散户同向"
    else:
        position_signal = "暂无席位数据"

    # 构建支撑理由
    reasons = []
    if summary.fundamental_score > 3:
        reasons.append(f"基本面看多 (+{summary.fundamental_score})")
    elif summary.fundamental_score < -3:
        reasons.append(f"基本面看空 ({summary.fundamental_score})")

    if summary.capital_score > 3:
        reasons.append(f"资金面看多 (+{summary.capital_score})")
    elif summary.capital_score < -3:
        reasons.append(f"资金面看空 ({summary.capital_score})")

    if summary.technical_score > 3:
        reasons.append(f"技术面看多 (+{summary.technical_score})")
    elif summary.technical_score < -3:
        reasons.append(f"技术面看空 ({summary.technical_score})")

    return {
        "variety_code": summary.comm_code,
        "direction": direction,
        "confidence": confidence,
        "total_score": total_score,
        "position_signal": position_signal,
        "reasons": reasons,
        "main_reason": summary.main_reason or "综合四维分析",
        "scores": {
            "fundamental": summary.fundamental_score,
            "capital": summary.capital_score,
            "technical": summary.technical_score,
            "message": summary.message_score
        }
    }


@router.get("/latest-strategies")
async def get_latest_strategies(
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """
    获取最新的策略列表
    """
    target_date = date.today()

    # 获取所有品种的最新策略
    summaries = db.query(MarketAnalysisSummary).filter(
        MarketAnalysisSummary.date == target_date
    ).order_by(
        desc(MarketAnalysisSummary.fundamental_score +
             MarketAnalysisSummary.capital_score +
             MarketAnalysisSummary.technical_score)
    ).limit(limit).all()

    strategies = []
    for s in summaries:
        strategies.append({
            "variety_code": s.comm_code,
            "direction": s.total_direction.value if s.total_direction else "中性",
            "total_score": (s.fundamental_score + s.capital_score +
                            s.technical_score + s.message_score),
            "reason": s.main_reason or ""
        })

    return {
        "date": str(target_date),
        "strategies": strategies
    }
