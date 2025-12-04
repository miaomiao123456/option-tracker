"""
资金面模块 API
提供席位持仓、资金流向等数据
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.database import get_db
from app.models.models import InstitutionalPosition, OptionFlow
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime, timedelta

router = APIRouter()


class PositionItem(BaseModel):
    """席位持仓数据"""
    broker_name: str
    net_position: int
    position_change: int
    win_rate: Optional[float]
    record_date: date

    class Config:
        from_attributes = True


@router.get("/{variety_code}/positions", response_model=List[PositionItem])
async def get_positions(
        variety_code: str,
        target_date: Optional[date] = None,
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db)
):
    """
    获取品种的席位持仓数据
    """
    if target_date is None:
        target_date = date.today()

    positions = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == target_date
    ).order_by(desc(InstitutionalPosition.net_position)).limit(limit).all()

    if not positions:
        raise HTTPException(status_code=404, detail=f"未找到品种 {variety_code} 在 {target_date} 的席位数据")

    return positions


@router.get("/{variety_code}/flow")
async def get_capital_flow(
        variety_code: str,
        days: int = Query(7, ge=1, le=30),
        db: Session = Depends(get_db)
):
    """
    获取品种的资金流向趋势
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # 按日期聚合
    flow_data = db.query(
        InstitutionalPosition.record_date,
        func.sum(InstitutionalPosition.net_position).label('total_net'),
        func.sum(InstitutionalPosition.position_change).label('total_change')
    ).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date.between(start_date, end_date)
    ).group_by(InstitutionalPosition.record_date).order_by(InstitutionalPosition.record_date).all()

    if not flow_data:
        return {
            "variety_code": variety_code,
            "flow_data": []
        }

    return {
        "variety_code": variety_code,
        "days": days,
        "flow_data": [
            {
                "date": str(item.record_date),
                "total_net_position": item.total_net,
                "total_change": item.total_change
            }
            for item in flow_data
        ]
    }


@router.get("/{variety_code}/top-brokers")
async def get_top_brokers(
        variety_code: str,
        limit: int = Query(10, ge=1, le=50),
        db: Session = Depends(get_db)
):
    """
    获取品种的Top席位排行
    """
    target_date = date.today()

    # 获取多头Top席位
    long_brokers = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == target_date,
        InstitutionalPosition.net_position > 0
    ).order_by(desc(InstitutionalPosition.net_position)).limit(limit).all()

    # 获取空头Top席位
    short_brokers = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == target_date,
        InstitutionalPosition.net_position < 0
    ).order_by(InstitutionalPosition.net_position).limit(limit).all()

    return {
        "variety_code": variety_code,
        "date": str(target_date),
        "top_long": [
            {
                "broker": b.broker_name,
                "position": b.net_position,
                "change": b.position_change,
                "win_rate": b.win_rate
            }
            for b in long_brokers
        ],
        "top_short": [
            {
                "broker": b.broker_name,
                "position": abs(b.net_position),
                "change": b.position_change,
                "win_rate": b.win_rate
            }
            for b in short_brokers
        ]
    }


@router.get("/{variety_code}/institution-vs-retail")
async def get_institution_vs_retail(
        variety_code: str,
        db: Session = Depends(get_db)
):
    """
    机构 vs 散户持仓对比
    """
    target_date = date.today()

    positions = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == target_date
    ).all()

    if not positions:
        raise HTTPException(status_code=404, detail=f"未找到数据")

    # 简单分类：假设前10大席位为机构，其他为散户
    sorted_positions = sorted(positions, key=lambda x: abs(x.net_position), reverse=True)

    institution_positions = sorted_positions[:10]
    retail_positions = sorted_positions[10:]

    institution_net = sum(p.net_position for p in institution_positions)
    retail_net = sum(p.net_position for p in retail_positions)

    institution_change = sum(p.position_change for p in institution_positions)
    retail_change = sum(p.position_change for p in retail_positions)

    return {
        "variety_code": variety_code,
        "date": str(target_date),
        "institution": {
            "net_position": institution_net,
            "position_change": institution_change,
            "direction": "long" if institution_net > 0 else "short"
        },
        "retail": {
            "net_position": retail_net,
            "position_change": retail_change,
            "direction": "long" if retail_net > 0 else "short"
        },
        "divergence": institution_net * retail_net < 0  # 机构和散户反向
    }


@router.get("/option-flow/all")
async def get_all_option_flow(
        hours: int = Query(1, ge=1, le=24),
        db: Session = Depends(get_db)
):
    """
    获取所有品种的期权资金流向汇总
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    flows = db.query(OptionFlow).filter(
        OptionFlow.record_time.between(start_time, end_time)
    ).all()

    if not flows:
        return {"varieties": [], "total_count": 0}

    # 按品种汇总
    variety_summary = {}
    for f in flows:
        code = f.comm_code
        if code not in variety_summary:
            variety_summary[code] = {
                "comm_code": code,
                "total_net_flow": 0,
                "total_volume": 0,
                "count": 0
            }
        variety_summary[code]["total_net_flow"] += f.net_flow or 0
        variety_summary[code]["total_volume"] += f.volume or 0
        variety_summary[code]["count"] += 1

    # 按净流入排序
    sorted_varieties = sorted(
        variety_summary.values(),
        key=lambda x: x["total_net_flow"],
        reverse=True
    )

    return {
        "varieties": sorted_varieties,
        "total_count": len(flows),
        "period_hours": hours
    }


@router.get("/{variety_code}/option-flow")
async def get_option_flow(
        variety_code: str,
        hours: int = Query(24, ge=1, le=72),
        db: Session = Depends(get_db)
):
    """
    获取品种的期权资金流向数据 (Openvlab数据)
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    flows = db.query(OptionFlow).filter(
        OptionFlow.comm_code == variety_code,
        OptionFlow.record_time.between(start_time, end_time)
    ).order_by(desc(OptionFlow.record_time)).all()

    if not flows:
        return {
            "variety_code": variety_code,
            "hours": hours,
            "option_flows": [],
            "summary": None
        }

    # 计算汇总数据
    total_net_flow = sum(f.net_flow or 0 for f in flows)
    total_volume = sum(f.volume or 0 for f in flows)

    return {
        "variety_code": variety_code,
        "hours": hours,
        "option_flows": [
            {
                "contract_code": f.contract_code,
                "net_flow": f.net_flow,
                "volume": f.volume,
                "change_ratio": f.change_ratio,
                "record_time": f.record_time.isoformat()
            }
            for f in flows
        ],
        "summary": {
            "total_net_flow": total_net_flow,
            "total_volume": total_volume,
            "flow_direction": "流入" if total_net_flow > 0 else "流出",
            "count": len(flows)
        }
    }
