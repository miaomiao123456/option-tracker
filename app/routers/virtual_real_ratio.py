"""
虚实比数据API路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date, datetime, timedelta

from app.models.database import get_db
from app.models.models import WarehouseReceipt
from pydantic import BaseModel


router = APIRouter()


# 响应模型
class VirtualRealRatioResponse(BaseModel):
    """虚实比数据响应"""
    id: int
    comm_code: str
    variety_name: str
    record_date: date
    receipt_quantity: float
    receipt_change: float
    main_contract: str
    open_interest: float
    open_interest_change: float
    contract_unit: float
    virtual_quantity: float
    virtual_real_ratio: float
    squeeze_risk: str
    impact_analysis: str
    price_pressure: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VirtualRealRatioSummary(BaseModel):
    """虚实比汇总统计"""
    total_varieties: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    high_risk_varieties: List[dict]


@router.get("/list", response_model=List[VirtualRealRatioResponse])
async def get_virtual_real_ratio_list(
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    comm_code: Optional[str] = Query(None, description="品种代码,如AU"),
    risk_level: Optional[str] = Query(None, description="风险等级: 高/中/低/无"),
    db: Session = Depends(get_db)
):
    """
    获取虚实比数据列表
    """
    query = db.query(WarehouseReceipt)

    # 日期筛选
    if query_date:
        target_date = datetime.strptime(query_date, "%Y-%m-%d").date()
        query = query.filter(WarehouseReceipt.record_date == target_date)
    else:
        # 默认返回最近一天的数据
        latest_date = db.query(WarehouseReceipt.record_date).order_by(
            desc(WarehouseReceipt.record_date)
        ).first()
        if latest_date:
            query = query.filter(WarehouseReceipt.record_date == latest_date[0])

    # 品种筛选
    if comm_code:
        query = query.filter(WarehouseReceipt.comm_code == comm_code.upper())

    # 风险等级筛选
    if risk_level:
        query = query.filter(WarehouseReceipt.squeeze_risk == risk_level)

    # 按虚实比降序排列
    results = query.order_by(desc(WarehouseReceipt.virtual_real_ratio)).all()

    return results


@router.get("/summary", response_model=VirtualRealRatioSummary)
async def get_virtual_real_ratio_summary(
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取虚实比汇总统计
    """
    # 确定查询日期
    if query_date:
        target_date = datetime.strptime(query_date, "%Y-%m-%d").date()
    else:
        latest_date = db.query(WarehouseReceipt.record_date).order_by(
            desc(WarehouseReceipt.record_date)
        ).first()
        target_date = latest_date[0] if latest_date else date.today()

    # 查询该日期的所有数据
    records = db.query(WarehouseReceipt).filter(
        WarehouseReceipt.record_date == target_date
    ).all()

    # 统计各风险等级数量
    high_risk = [r for r in records if r.squeeze_risk == "高"]
    medium_risk = [r for r in records if r.squeeze_risk == "中"]
    low_risk = [r for r in records if r.squeeze_risk == "低"]

    # 高风险品种详情
    high_risk_varieties = [
        {
            "comm_code": r.comm_code,
            "variety_name": r.variety_name,
            "virtual_real_ratio": round(r.virtual_real_ratio, 2),
            "impact": r.impact_analysis
        }
        for r in sorted(high_risk, key=lambda x: x.virtual_real_ratio, reverse=True)
    ]

    return VirtualRealRatioSummary(
        total_varieties=len(records),
        high_risk_count=len(high_risk),
        medium_risk_count=len(medium_risk),
        low_risk_count=len(low_risk),
        high_risk_varieties=high_risk_varieties
    )


@router.get("/detail/{comm_code}", response_model=VirtualRealRatioResponse)
async def get_virtual_real_ratio_detail(
    comm_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取指定品种的虚实比详情
    """
    # 确定查询日期
    if query_date:
        target_date = datetime.strptime(query_date, "%Y-%m-%d").date()
    else:
        latest_date = db.query(WarehouseReceipt.record_date).order_by(
            desc(WarehouseReceipt.record_date)
        ).first()
        target_date = latest_date[0] if latest_date else date.today()

    record = db.query(WarehouseReceipt).filter(
        WarehouseReceipt.comm_code == comm_code.upper(),
        WarehouseReceipt.record_date == target_date
    ).first()

    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"未找到品种 {comm_code} 在日期 {target_date} 的数据")

    return record


@router.get("/history/{comm_code}")
async def get_virtual_real_ratio_history(
    comm_code: str,
    days: int = Query(30, description="查询天数", ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    获取指定品种的虚实比历史数据
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    records = db.query(WarehouseReceipt).filter(
        WarehouseReceipt.comm_code == comm_code.upper(),
        WarehouseReceipt.record_date >= start_date,
        WarehouseReceipt.record_date <= end_date
    ).order_by(WarehouseReceipt.record_date).all()

    # 格式化为图表数据
    dates = [r.record_date.strftime("%Y-%m-%d") for r in records]
    ratios = [round(r.virtual_real_ratio, 2) for r in records]
    receipts = [r.receipt_quantity for r in records]
    interests = [r.open_interest for r in records]
    risks = [r.squeeze_risk for r in records]

    return {
        "success": True,
        "comm_code": comm_code.upper(),
        "variety_name": records[0].variety_name if records else "",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "data": {
            "dates": dates,
            "virtual_real_ratios": ratios,
            "receipt_quantities": receipts,
            "open_interests": interests,
            "squeeze_risks": risks
        }
    }


@router.post("/refresh")
async def refresh_virtual_real_ratio_data(
    comm_code: Optional[str] = Query(None, description="品种代码,为空则刷新所有"),
    db: Session = Depends(get_db)
):
    """
    手动刷新虚实比数据
    """
    from app.crawlers.virtual_real_ratio_spider import VirtualRealRatioSpider

    spider = VirtualRealRatioSpider(db=db)

    if comm_code:
        # 刷新单个品种
        success = spider.crawl_single_variety(comm_code.upper())
        return {
            "success": success,
            "message": f"品种 {comm_code} 数据{'刷新成功' if success else '刷新失败'}"
        }
    else:
        # 刷新所有品种
        results = spider.crawl_all_varieties()
        success_count = sum(1 for v in results.values() if v)
        return {
            "success": True,
            "message": f"成功刷新 {success_count}/{len(results)} 个品种",
            "details": results
        }
