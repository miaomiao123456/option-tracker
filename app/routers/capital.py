"""
资金面模块 API
提供席位持仓、资金流向等数据
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.database import get_db
from app.models.models import InstitutionalPosition, OptionFlow, Commodity
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime, timedelta
from app.crawlers.jiaoyikecha_spider import JiaoyikechaSpider
import logging

logger = logging.getLogger(__name__)
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


@router.get("/{variety_code}/position-trend")
async def get_position_trend(
        variety_code: str,
        days: int = Query(30, ge=7, le=90),
        target_date: Optional[date] = Query(None, description="目标日期，默认为最新数据日期"),
        db: Session = Depends(get_db)
):
    """
    获取品种的多空持仓趋势（用于绘制走势图）
    返回格式: {dates: [...], long_positions: [...], short_positions: [...], net_positions: [...]}
    """
    # 如果指定了target_date，以它为end_date；否则使用最新数据日期
    if target_date:
        end_date = target_date
    else:
        # 查询该品种最新的数据日期
        latest_record = db.query(InstitutionalPosition).filter(
            InstitutionalPosition.comm_code == variety_code
        ).order_by(desc(InstitutionalPosition.record_date)).first()
        end_date = latest_record.record_date if latest_record else date.today()

    start_date = end_date - timedelta(days=days)

    # 查询市场总持仓数据（包含多空分离信息）
    positions = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date.between(start_date, end_date),
        InstitutionalPosition.broker_name.like('%市场总持仓%')
    ).order_by(InstitutionalPosition.record_date).all()

    if not positions:
        return {
            "variety_code": variety_code,
            "dates": [],
            "long_positions": [],
            "short_positions": [],
            "net_positions": []
        }

    # 从broker_name中解析多空持仓 "市场总持仓(多:374827|空:398980)"
    dates = []
    long_positions = []
    short_positions = []
    net_positions = []

    import re
    for p in positions:
        dates.append(str(p.record_date))
        net_positions.append(p.net_position)

        # 从broker_name中提取多空数据
        match = re.search(r'多:(\d+)\|空:(\d+)', p.broker_name)
        if match:
            long_pos = int(match.group(1))
            short_pos = int(match.group(2))
            long_positions.append(long_pos)
            short_positions.append(short_pos)
        else:
            # 如果无法解析，使用净持仓推算
            if p.net_position > 0:
                long_positions.append(abs(p.net_position))
                short_positions.append(0)
            else:
                long_positions.append(0)
                short_positions.append(abs(p.net_position))

    return {
        "variety_code": variety_code,
        "dates": dates,
        "long_positions": long_positions,
        "short_positions": short_positions,
        "net_positions": net_positions,
        "days": days
    }


@router.get("/{variety_code}/top-brokers")
async def get_top_brokers(
        variety_code: str,
        limit: int = Query(10, ge=1, le=50),
        target_date: Optional[date] = Query(None, description="目标日期，默认为最新数据日期"),
        db: Session = Depends(get_db)
):
    """
    获取品种的Top席位排行
    支持按日期查询历史数据
    """
    # 如果指定了target_date，使用该日期；否则查询最新数据日期
    if target_date:
        # 检查该日期是否有数据
        has_data = db.query(InstitutionalPosition).filter(
            InstitutionalPosition.comm_code == variety_code,
            InstitutionalPosition.record_date == target_date
        ).first()

        if not has_data:
            # 如果指定日期没数据，尝试获取最近的数据日期
            latest_record = db.query(InstitutionalPosition).filter(
                InstitutionalPosition.comm_code == variety_code,
                InstitutionalPosition.record_date <= target_date
            ).order_by(desc(InstitutionalPosition.record_date)).first()

            if latest_record:
                target_date = latest_record.record_date
            else:
                return {
                    "variety_code": variety_code,
                    "date": str(target_date),
                    "top_long": [],
                    "top_short": [],
                    "message": f"未找到 {target_date} 及之前的数据"
                }
    else:
        # 查询该品种最新的数据日期
        latest_record = db.query(InstitutionalPosition).filter(
            InstitutionalPosition.comm_code == variety_code
        ).order_by(desc(InstitutionalPosition.record_date)).first()

        if not latest_record:
            return {
                "variety_code": variety_code,
                "date": str(date.today()),
                "top_long": [],
                "top_short": []
            }

        target_date = latest_record.record_date

    # 获取多头Top席位 (排除市场总持仓)
    long_brokers = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == target_date,
        InstitutionalPosition.net_position > 0,
        ~InstitutionalPosition.broker_name.like('%市场总持仓%')
    ).order_by(desc(InstitutionalPosition.net_position)).limit(limit).all()

    # 获取空头Top席位 (排除市场总持仓)
    short_brokers = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == target_date,
        InstitutionalPosition.net_position < 0,
        ~InstitutionalPosition.broker_name.like('%市场总持仓%')
    ).order_by(InstitutionalPosition.net_position).limit(limit).all()

    # 如果没有具体席位数据，尝试获取市场总持仓数据
    market_summary = None
    if not long_brokers and not short_brokers:
        market_record = db.query(InstitutionalPosition).filter(
            InstitutionalPosition.comm_code == variety_code,
            InstitutionalPosition.record_date == target_date,
            InstitutionalPosition.broker_name.like('%市场总持仓%')
        ).first()

        if market_record:
            # 从broker_name中解析多空持仓 "市场总持仓(多:374827|空:398980)"
            import re
            match = re.search(r'多:(\d+)\|空:(\d+)', market_record.broker_name)
            if match:
                long_pos = int(match.group(1))
                short_pos = int(match.group(2))
                market_summary = {
                    "long_total": long_pos,
                    "short_total": short_pos,
                    "net_position": long_pos - short_pos,
                    "position_change": market_record.position_change
                }

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
        ],
        "market_summary": market_summary
    }


@router.get("/{variety_code}/institution-vs-retail")
async def get_institution_vs_retail(
        variety_code: str,
        target_date: Optional[date] = Query(None, description="目标日期，默认为最新数据日期"),
        db: Session = Depends(get_db)
):
    """
    机构 vs 散户持仓对比
    支持按日期查询历史数据
    """
    # 如果指定了target_date，使用该日期；否则查询最新数据日期
    if target_date:
        query_date = target_date
    else:
        latest_record = db.query(InstitutionalPosition).filter(
            InstitutionalPosition.comm_code == variety_code
        ).order_by(desc(InstitutionalPosition.record_date)).first()
        query_date = latest_record.record_date if latest_record else date.today()

    positions = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == query_date
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
    修改:基于commodities主品种列表返回所有品种,无数据显示null
    """
    # 获取所有品种列表
    all_commodities = db.query(Commodity).all()
    commodity_dict = {c.code: c.name for c in all_commodities}

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    flows = db.query(OptionFlow).filter(
        OptionFlow.record_time.between(start_time, end_time)
    ).all()

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

    # 构建所有品种的返回数据
    all_varieties = []
    for code, name in commodity_dict.items():
        if code in variety_summary:
            all_varieties.append(variety_summary[code])
        else:
            # 无数据的品种
            all_varieties.append({
                "comm_code": code,
                "total_net_flow": None,
                "total_volume": None,
                "count": 0
            })

    # 按净流入排序(null值排最后)
    all_varieties.sort(
        key=lambda x: x["total_net_flow"] if x["total_net_flow"] is not None else -999999,
        reverse=True
    )

    return {
        "varieties": all_varieties,
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


@router.get("/jiaoyikecha/{variety_name}/{contract_code}")
async def get_jiaoyikecha_positions(
        variety_name: str,
        contract_code: str,
        target_date: Optional[date] = None
):
    """
    从交易可查网站实时获取席位持仓数据

    参数:
    - variety_name: 品种中文名称(如"螺纹钢")
    - contract_code: 合约代码(如"rb2605")
    - target_date: 查询日期(默认今天，如无数据自动回退到前一天)

    返回: 多头和空头前20席位数据
    """
    if target_date is None:
        target_date = date.today()

    try:
        spider = JiaoyikechaSpider()

        # 获取席位数据，如果今天没数据，自动回退到前几天
        result = None
        actual_date = target_date
        for days_back in range(4):  # 最多回退3天
            query_date = target_date - timedelta(days=days_back)
            result = spider.fetch_position_data(
                variety=variety_name,
                contract_code=contract_code,
                query_date=query_date
            )
            if result.get('success') and result.get('long_positions'):
                actual_date = query_date
                logger.info(f"成功获取 {variety_name}/{contract_code} 在 {actual_date} 的席位数据")
                break
            logger.info(f"{variety_name}/{contract_code} 在 {query_date} 无数据，尝试前一天...")

        if not result.get('success') or not result.get('long_positions'):
            raise HTTPException(
                status_code=500,
                detail=f"获取数据失败: {result.get('error', '最近几天都没有席位数据')}"
            )

        return {
            "success": True,
            "variety": variety_name,
            "contract_code": contract_code,
            "date": str(actual_date),
            "long_positions": result['long_positions'],
            "short_positions": result['short_positions'],
            "long_top5_total": result['long_top5_total'],
            "short_top5_total": result['short_top5_total'],
            "long_short_ratio": round(result['long_top5_total'] / result['short_top5_total'], 4) if result['short_top5_total'] > 0 else None
        }

    except Exception as e:
        logger.error(f"获取交易可查数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


@router.get("/jiaoyikecha/{variety_name}/{contract_code}/full")
async def get_jiaoyikecha_full_data(
        variety_name: str,
        contract_code: str,
        target_date: Optional[date] = None
):
    """
    从交易可查网站获取完整的持仓数据,包括历史趋势图数据

    参数:
    - variety_name: 品种中文名称(如"螺纹钢")
    - contract_code: 合约代码(如"rb2605")
    - target_date: 查询日期(默认今天，如无数据自动回退到前一天)

    返回: 包含buy, ss, total_buy, total_ss, dates, net_buy, net_ss等完整数据
    """
    if target_date is None:
        target_date = date.today()

    try:
        spider = JiaoyikechaSpider()

        # 获取完整数据，如果今天没数据，自动回退到前几天
        result = None
        actual_date = target_date
        for days_back in range(4):  # 最多回退3天
            query_date = target_date - timedelta(days=days_back)
            result = spider.fetch_full_position_data(
                variety=variety_name,
                contract_code=contract_code,
                query_date=query_date
            )
            if result.get('success') and result.get('data', {}).get('buy'):
                actual_date = query_date
                logger.info(f"成功获取 {variety_name}/{contract_code} 在 {actual_date} 的完整席位数据")
                break
            logger.info(f"{variety_name}/{contract_code} 在 {query_date} 无完整数据，尝试前一天...")

        if not result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"获取数据失败: {result.get('error', '未知错误')}"
            )

        return {
            "success": True,
            "variety": variety_name,
            "contract_code": contract_code,
            "date": str(actual_date),
            "data": result['data']
        }

    except Exception as e:
        logger.error(f"获取交易可查完整数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


# 机构散户方向相反扫描结果存储（使用文件存储，简单方案）
import json
import os

DIVERGENT_SCAN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'divergent_scan_result.json')


@router.post("/divergent-scan/save")
async def save_divergent_scan(data: dict):
    """保存机构散户方向相反扫描结果"""
    try:
        with open(DIVERGENT_SCAN_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"success": True, "message": "保存成功"}
    except Exception as e:
        logger.error(f"保存扫描结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/divergent-scan/latest")
async def get_divergent_scan():
    """获取最新的机构散户方向相反扫描结果"""
    try:
        if os.path.exists(DIVERGENT_SCAN_FILE):
            with open(DIVERGENT_SCAN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        return {"varieties": [], "update_time": None}
    except Exception as e:
        logger.error(f"读取扫描结果失败: {e}")
        return {"varieties": [], "update_time": None}


class SeasonalPriceRequest(BaseModel):
    """价格季节性分析请求"""
    variety: str
    contracts: List[str]


@router.post("/seasonal-price")
async def get_seasonal_price(request: SeasonalPriceRequest):
    """
    获取多个合约的历史价格数据用于季节性对比
    使用 akshare 获取期货合约价格数据
    """
    try:
        import akshare as ak

        result_data = []

        for contract in request.contracts:
            try:
                # 尝试获取合约历史数据
                # akshare 获取期货历史数据
                symbol = contract.upper()

                try:
                    # 尝试获取日线数据
                    df = ak.futures_zh_daily_sina(symbol=symbol)

                    if df is not None and len(df) > 0:
                        # 提取收盘价
                        prices = df['收盘价'].tolist() if '收盘价' in df.columns else df['close'].tolist()
                        dates = df['日期'].tolist() if '日期' in df.columns else df.index.tolist()

                        result_data.append({
                            "contract": contract,
                            "prices": prices[-60:] if len(prices) > 60 else prices,  # 最近60个交易日
                            "dates": [str(d) for d in dates[-60:]] if len(dates) > 60 else [str(d) for d in dates]
                        })
                    else:
                        result_data.append({
                            "contract": contract,
                            "prices": [],
                            "dates": []
                        })
                except Exception as e:
                    logger.warning(f"获取 {contract} 数据失败: {e}")
                    result_data.append({
                        "contract": contract,
                        "prices": [],
                        "dates": []
                    })

            except Exception as e:
                logger.error(f"处理合约 {contract} 失败: {e}")
                result_data.append({
                    "contract": contract,
                    "prices": [],
                    "dates": []
                })

        return {
            "success": True,
            "data": result_data
        }

    except ImportError:
        logger.error("akshare 未安装")
        return {
            "success": False,
            "error": "akshare 库未安装",
            "data": []
        }
    except Exception as e:
        logger.error(f"获取价格季节性数据失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }
