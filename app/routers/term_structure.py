"""
期限结构模块 API
提供期货合约期限结构数据
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
import json
from datetime import datetime, date
from pathlib import Path
import logging

from app.models.database import get_db
from app.models.models import TermStructureHistory, Commodity
from app.services.term_structure_analyzer import TermStructureAnalyzer

try:
    import akshare as ak
except ImportError:
    ak = None
    logger.warning("akshare未安装,部分功能可能不可用")

logger = logging.getLogger(__name__)

router = APIRouter()


def load_term_structure_data():
    """
    从JSON文件加载期限结构数据 (推荐品种,S/A级)
    """
    data_file = Path(__file__).parent.parent.parent / "data" / "term_structure_data.json"

    if not data_file.exists():
        logger.warning(f"期限结构数据文件不存在: {data_file}")
        return None

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"加载期限结构数据失败: {e}")
        return None


def load_all_term_structure_data():
    """
    从JSON文件加载所有品种的期限结构数据
    """
    data_file = Path(__file__).parent.parent.parent / "data" / "term_structure_data_all.json"

    if not data_file.exists():
        logger.warning(f"所有品种数据文件不存在: {data_file}")
        return None

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"加载所有品种数据失败: {e}")
        return None


@router.get("/varieties")
async def get_available_varieties(db: Session = Depends(get_db)):
    """
    获取可用的期货品种列表
    优先从数据库获取，备选从JSON数据获取
    """
    try:
        # 优先从数据库获取品种列表
        commodities = db.query(Commodity).all()
        if commodities:
            varieties = [
                {"code": c.code, "name": c.name}
                for c in commodities
            ]
            return {
                "success": True,
                "varieties": varieties
            }

        # 备选：从JSON数据文件获取
        all_data = load_all_term_structure_data()
        if all_data:
            varieties = [
                {"code": code, "name": data.get("variety_name", code)}
                for code, data in all_data.items()
            ]
            return {
                "success": True,
                "varieties": varieties
            }

        # 如果都没有，返回空列表
        return {
            "success": True,
            "varieties": []
        }
    except Exception as e:
        logger.error(f"获取品种列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/structure/{variety_code}")
async def get_term_structure(
    variety_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD")
):
    """
    获取指定品种的期限结构数据

    返回该品种所有有效合约的价格，用于绘制期限结构曲线
    """
    try:
        variety_code = variety_code.upper()

        # 先从推荐品种数据中查找
        recommended_data = load_term_structure_data()
        variety_data = recommended_data.get(variety_code) if recommended_data else None

        # 如果推荐数据中没有，再从全部品种数据中查找
        if not variety_data:
            all_data = load_all_term_structure_data()
            variety_data = all_data.get(variety_code) if all_data else None

        if not variety_data:
            return {
                "success": False,
                "variety_code": variety_code,
                "message": f"未找到品种 {variety_code} 的数据",
                "contracts": []
            }

        return {
            "success": True,
            "variety_code": variety_data["variety_code"],
            "query_date": query_date or date.today().strftime('%Y-%m-%d'),
            "market_structure": variety_data["market_structure"],
            "structure_desc": variety_data["structure_desc"],
            "trade_suggestion": variety_data["trade_suggestion"],
            "trade_reason": variety_data["trade_reason"],
            "contracts": variety_data["contracts"],
            "total_contracts": variety_data["total_contracts"],
            "update_time": variety_data.get("update_time", "")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取期限结构失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all-structures")
async def get_all_term_structures(
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取所有品种的期限结构数据 (包含所有品种)
    修改:基于commodities主品种列表返回所有品种,无数据显示null
    支持按日期查询数据库历史数据

    返回所有支持品种的期限结构汇总,包括Contango和Backwardation分类
    """
    try:
        # 获取所有品种列表
        all_commodities = db.query(Commodity).all()
        commodity_dict = {c.code: c.name for c in all_commodities}

        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            target_date = date.today()

        # 优先从数据库查询指定日期的数据
        db_records = db.query(TermStructureHistory).filter(
            TermStructureHistory.record_date == target_date
        ).all()

        # 如果指定日期没有数据，尝试获取最近的数据日期
        actual_data_date = target_date
        if not db_records:
            latest_record = db.query(TermStructureHistory).order_by(
                TermStructureHistory.record_date.desc()
            ).first()
            if latest_record:
                actual_data_date = latest_record.record_date
                db_records = db.query(TermStructureHistory).filter(
                    TermStructureHistory.record_date == actual_data_date
                ).all()

        all_data = {}
        data_source = "database"

        if db_records:
            # 使用数据库数据，包含合约列表
            for record in db_records:
                # 解析合约JSON数据
                contracts = []
                if record.contracts_json:
                    try:
                        contracts = json.loads(record.contracts_json)
                    except:
                        contracts = []

                all_data[record.comm_code] = {
                    "variety_code": record.comm_code,
                    "variety_name": record.variety_name or record.comm_code,
                    "market_structure": record.market_structure,
                    "structure_desc": record.structure_desc,
                    "trade_suggestion": record.trade_suggestion,
                    "trade_reason": None,
                    "contracts": contracts,
                    "total_contracts": len(contracts),
                    "grade": record.grade,
                    "structure_score": record.structure_score,
                    "recommend": bool(record.recommend),
                    "update_time": record.record_date.strftime('%Y-%m-%d') if record.record_date else ""
                }
        else:
            # 如果数据库没有该日期数据，回退到JSON文件
            all_data = load_all_term_structure_data() or {}
            data_source = "json_file"

        if not all_data:
            # 如果没有数据,返回所有品种的null记录
            return {
                "success": True,
                "query_date": target_date.strftime('%Y-%m-%d'),
                "data_source": data_source,
                "total_varieties": len(commodity_dict),
                "contango_count": 0,
                "backwardation_count": 0,
                "contango_varieties": [],
                "backwardation_varieties": []
            }

        contango_varieties = []  # Contango结构品种(做空)
        backwardation_varieties = []  # Backwardation结构品种(做多)

        # 基于所有品种构建返回数据
        for code, name in commodity_dict.items():
            if code in all_data:
                # 有数据的品种
                variety_data = all_data[code]
                variety_info = {
                    "variety_code": variety_data.get("variety_code", code),
                    "variety_name": variety_data.get("variety_name", name),
                    "market_structure": variety_data.get("market_structure"),
                    "structure_desc": variety_data.get("structure_desc"),
                    "trade_suggestion": variety_data.get("trade_suggestion"),
                    "trade_reason": variety_data.get("trade_reason"),
                    "contracts": variety_data.get("contracts", []),
                    "total_contracts": variety_data.get("total_contracts", 0),
                    "grade": variety_data.get("grade", "C"),
                    "structure_score": variety_data.get("structure_score", 0),
                    "recommend": variety_data.get("recommend", False),
                    "update_time": variety_data.get("update_time", "")
                }

                # 根据市场结构分类
                market_structure = variety_data.get("market_structure")
                if market_structure == "正向市场":
                    contango_varieties.append(variety_info)
                elif market_structure == "反向市场":
                    backwardation_varieties.append(variety_info)
            else:
                # 无数据的品种 - 返回null结构
                variety_info = {
                    "variety_code": code,
                    "variety_name": name,
                    "market_structure": None,
                    "structure_desc": None,
                    "trade_suggestion": None,
                    "trade_reason": None,
                    "contracts": [],
                    "total_contracts": 0,
                    "grade": None,
                    "structure_score": None,
                    "recommend": False,
                    "update_time": None
                }
                # 无数据的品种不分类,不添加到contango或backwardation列表

        return {
            "success": True,
            "query_date": target_date.strftime('%Y-%m-%d'),
            "actual_data_date": actual_data_date.strftime('%Y-%m-%d'),
            "data_date_mismatch": target_date != actual_data_date,
            "data_source": data_source,
            "total_varieties": len(commodity_dict),
            "contango_count": len(contango_varieties),
            "backwardation_count": len(backwardation_varieties),
            "contango_varieties": contango_varieties,
            "backwardation_varieties": backwardation_varieties
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取所有期限结构失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommended-structures")
async def get_recommended_term_structures(query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD")):
    """
    获取推荐的期限结构品种 (S/A级)

    返回最符合Contango/Backwardation结构的品种
    """
    try:
        # 从JSON文件加载推荐品种数据
        recommended_data = load_term_structure_data()

        if recommended_data is None:
            raise HTTPException(
                status_code=500,
                detail="无法加载推荐品种数据,请稍后重试"
            )

        contango_varieties = []  # Contango结构品种(做空)
        backwardation_varieties = []  # Backwardation结构品种(做多)

        # 分类推荐品种
        for variety_code, variety_data in recommended_data.items():
            variety_info = {
                "variety_code": variety_data["variety_code"],
                "variety_name": variety_data["variety_name"],
                "market_structure": variety_data["market_structure"],
                "structure_desc": variety_data["structure_desc"],
                "trade_suggestion": variety_data["trade_suggestion"],
                "trade_reason": variety_data["trade_reason"],
                "contracts": variety_data["contracts"],
                "total_contracts": variety_data["total_contracts"],
                "grade": variety_data.get("grade", "A"),
                "structure_score": variety_data.get("structure_score", 0),
                "update_time": variety_data.get("update_time", "")
            }

            # 根据市场结构分类
            if variety_data["market_structure"] == "正向市场":
                contango_varieties.append(variety_info)
            elif variety_data["market_structure"] == "反向市场":
                backwardation_varieties.append(variety_info)

        # 按得分排序
        contango_varieties.sort(key=lambda x: x['structure_score'], reverse=True)
        backwardation_varieties.sort(key=lambda x: x['structure_score'], reverse=True)

        return {
            "success": True,
            "query_date": query_date or date.today().strftime('%Y-%m-%d'),
            "total_varieties": len(recommended_data),
            "contango_count": len(contango_varieties),
            "backwardation_count": len(backwardation_varieties),
            "contango_varieties": contango_varieties,
            "backwardation_varieties": backwardation_varieties
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取推荐期限结构失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{variety_code}")
async def get_term_structure_analysis(variety_code: str):
    """
    获取期限结构分析
    包括展期收益率、套利机会等
    """
    try:
        variety_code = variety_code.upper()

        # 获取期限结构数据
        structure_response = await get_term_structure(variety_code)

        if not structure_response['success']:
            return structure_response

        contracts = structure_response['contracts']

        if len(contracts) < 2:
            return {
                "success": False,
                "message": "合约数量不足，无法进行分析"
            }

        # 计算相邻合约价差和年化展期收益率
        spreads = []
        for i in range(len(contracts) - 1):
            near = contracts[i]
            far = contracts[i + 1]

            price_diff = far['price'] - near['price']
            price_diff_pct = (price_diff / near['price']) * 100

            # 计算月份差异（简化计算）
            try:
                near_month = int(near['month'][-2:])  # 取最后两位作为月份
                far_month = int(far['month'][-2:])
                month_diff = far_month - near_month
                if month_diff <= 0:
                    month_diff += 12

                # 年化收益率
                annualized_return = (price_diff_pct / month_diff) * 12
            except:
                month_diff = 1
                annualized_return = 0

            spreads.append({
                "near_contract": near['symbol'],
                "far_contract": far['symbol'],
                "price_diff": round(price_diff, 2),
                "price_diff_pct": round(price_diff_pct, 2),
                "annualized_return": round(annualized_return, 2),
                "month_diff": month_diff
            })

        # 寻找套利机会
        arbitrage_opportunities = []
        for spread in spreads:
            if abs(spread['annualized_return']) > 10:  # 年化收益率超过10%
                direction = "做多近月做空远月" if spread['annualized_return'] < 0 else "做多远月做空近月"
                arbitrage_opportunities.append({
                    "spread": f"{spread['near_contract']}-{spread['far_contract']}",
                    "annualized_return": spread['annualized_return'],
                    "direction": direction,
                    "risk_level": "高" if abs(spread['annualized_return']) > 20 else "中"
                })

        return {
            "success": True,
            "variety_code": variety_code,
            "market_structure": structure_response['market_structure'],
            "structure_desc": structure_response['structure_desc'],
            "spreads": spreads,
            "arbitrage_opportunities": arbitrage_opportunities,
            "total_opportunities": len(arbitrage_opportunities)
        }

    except Exception as e:
        logger.error(f"期限结构分析失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ========== Phase 3 新增API端点 ==========

@router.get("/latest-date")
async def get_latest_term_structure_date(db: Session = Depends(get_db)):
    """
    获取数据库中最新的期限结构日期
    用于前端日期选择器默认值
    """
    try:
        from sqlalchemy import desc

        latest_record = db.query(TermStructureHistory.record_date).order_by(
            desc(TermStructureHistory.record_date)
        ).first()

        if latest_record:
            return {
                "success": True,
                "latest_date": latest_record[0].strftime('%Y-%m-%d')
            }
        else:
            return {
                "success": True,
                "latest_date": date.today().strftime('%Y-%m-%d')
            }
    except Exception as e:
        logger.error(f"获取最新日期失败: {e}")
        return {
            "success": False,
            "latest_date": date.today().strftime('%Y-%m-%d')
        }


@router.get("/history/{comm_code}")
async def get_term_structure_history(
    comm_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取指定品种的期限结构历史记录
    (Phase 3: 从数据库获取,支持历史查询)
    """
    try:
        comm_code = comm_code.upper()

        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            # 获取最新日期
            from sqlalchemy import desc
            latest_record = db.query(TermStructureHistory.record_date).order_by(
                desc(TermStructureHistory.record_date)
            ).first()
            target_date = latest_record[0] if latest_record else date.today()

        # 查询历史记录
        record = db.query(TermStructureHistory).filter(
            TermStructureHistory.comm_code == comm_code,
            TermStructureHistory.record_date == target_date
        ).first()

        if not record:
            return {
                "success": False,
                "comm_code": comm_code,
                "message": f"未找到 {comm_code} 在 {target_date} 的期限结构数据"
            }

        return {
            "success": True,
            "comm_code": record.comm_code,
            "variety_name": record.variety_name,
            "record_date": record.record_date.strftime('%Y-%m-%d'),
            "structure_type": record.structure_type,
            "market_structure": record.market_structure,
            "structure_desc": record.structure_desc,
            "near_contract": record.near_contract,
            "far_contract": record.far_contract,
            "near_price": record.near_price,
            "far_price": record.far_price,
            "price_spread": record.price_spread,
            "spread_pct": record.spread_pct,
            "structure_score": record.structure_score,
            "grade": record.grade,
            "recommend": bool(record.recommend),
            "trade_suggestion": record.trade_suggestion
        }

    except Exception as e:
        logger.error(f"获取期限结构历史失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversion-signal/{comm_code}")
async def get_structure_conversion_signal(
    comm_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    lookback_days: int = Query(7, description="回溯天数"),
    db: Session = Depends(get_db)
):
    """
    获取期限结构转换信号 (Phase 3.5核心功能)
    检测 Contango ↔ Backwardation 转换
    """
    try:
        comm_code = comm_code.upper()

        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            from sqlalchemy import desc
            latest_record = db.query(TermStructureHistory.record_date).order_by(
                desc(TermStructureHistory.record_date)
            ).first()
            target_date = latest_record[0] if latest_record else date.today()

        # 创建分析器
        analyzer = TermStructureAnalyzer(db)

        # 检测转换信号
        conversion = analyzer.detect_structure_conversion(
            comm_code, target_date, lookback_days
        )

        return {
            "success": True,
            "comm_code": comm_code,
            "analysis_date": target_date.strftime('%Y-%m-%d'),
            **conversion
        }

    except Exception as e:
        logger.error(f"获取结构转换信号失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spread-analysis/{comm_code}")
async def get_spread_analysis(
    comm_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取价差历史分析 (Phase 3.6核心功能)
    包含: 百分位、Z-score、变化率
    """
    try:
        comm_code = comm_code.upper()

        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            from sqlalchemy import desc
            latest_record = db.query(TermStructureHistory.record_date).order_by(
                desc(TermStructureHistory.record_date)
            ).first()
            target_date = latest_record[0] if latest_record else date.today()

        # 创建分析器
        analyzer = TermStructureAnalyzer(db)

        # 价差分析
        spread_analysis = analyzer.analyze_spread_history(comm_code, target_date)

        return {
            "success": True,
            "comm_code": comm_code,
            "analysis_date": target_date.strftime('%Y-%m-%d'),
            **spread_analysis
        }

    except Exception as e:
        logger.error(f"获取价差分析失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enhanced-analysis/{comm_code}")
async def get_term_structure_enhanced_analysis(
    comm_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取期限结构增强分析 (Phase 3完整功能)
    包含: 结构转换信号 + 价差分析 + 综合得分
    """
    try:
        comm_code = comm_code.upper()

        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            from sqlalchemy import desc
            latest_record = db.query(TermStructureHistory.record_date).order_by(
                desc(TermStructureHistory.record_date)
            ).first()
            target_date = latest_record[0] if latest_record else date.today()

        # 创建分析器
        analyzer = TermStructureAnalyzer(db)

        # 计算所有增强指标
        result = analyzer.calculate_all_enhancements(comm_code, target_date)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error(f"获取期限结构增强分析失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/score/{comm_code}")
async def get_term_structure_score(
    comm_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取期限结构得分 (用于多维度综合分析)
    返回: -5 到 +5 的得分和理由
    """
    try:
        comm_code = comm_code.upper()

        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            from sqlalchemy import desc
            latest_record = db.query(TermStructureHistory.record_date).order_by(
                desc(TermStructureHistory.record_date)
            ).first()
            target_date = latest_record[0] if latest_record else date.today()

        # 创建分析器
        analyzer = TermStructureAnalyzer(db)

        # 获取得分
        score, reasons = analyzer.get_term_structure_score_for_综合分析(
            comm_code, target_date
        )

        return {
            "success": True,
            "comm_code": comm_code,
            "analysis_date": target_date.strftime('%Y-%m-%d'),
            "score": score,
            "reasons": reasons
        }

    except Exception as e:
        logger.error(f"获取期限结构得分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/structure-changes")
async def get_structure_changes(
    lookback_days: int = Query(7, description="回溯天数"),
    db: Session = Depends(get_db)
):
    """
    获取所有品种的结构变化信息
    用于展示最近有 Contango ↔ Backwardation 转换的品种
    """
    try:
        from sqlalchemy import desc, distinct

        # 获取最新日期
        latest_record = db.query(TermStructureHistory.record_date).order_by(
            desc(TermStructureHistory.record_date)
        ).first()
        target_date = latest_record[0] if latest_record else date.today()

        # 获取所有有数据的品种代码
        all_comm_codes = db.query(distinct(TermStructureHistory.comm_code)).filter(
            TermStructureHistory.record_date == target_date
        ).all()
        comm_codes = [r[0] for r in all_comm_codes]

        # 创建分析器
        analyzer = TermStructureAnalyzer(db)

        # 存储有变化的品种
        changed_varieties = []
        all_varieties = []

        for comm_code in comm_codes:
            # 获取转换信号
            conversion = analyzer.detect_structure_conversion(
                comm_code, target_date, lookback_days
            )

            # 获取当前记录
            current = db.query(TermStructureHistory).filter(
                TermStructureHistory.comm_code == comm_code,
                TermStructureHistory.record_date == target_date
            ).first()

            if not current:
                continue

            variety_info = {
                "variety_code": comm_code,
                "variety_name": current.variety_name or comm_code,
                "current_structure": conversion["current_structure"],
                "past_structure": conversion["past_structure"],
                "has_conversion": conversion["has_conversion"],
                "conversion_type": conversion["conversion_type"],
                "conversion_strength": conversion["conversion_strength"],
                "days_since_conversion": conversion["days_since_conversion"],
                "signal_description": conversion["signal_description"],
                "current_spread": conversion.get("current_spread"),
                "spread_change": conversion.get("spread_change"),
                "spread_change_pct": conversion.get("spread_change_pct"),
                "trade_suggestion": current.trade_suggestion,
                "grade": current.grade
            }

            all_varieties.append(variety_info)

            # 只添加有转换的品种到变化列表
            if conversion["has_conversion"]:
                changed_varieties.append(variety_info)

        # 按转换强度排序 (强 > 中 > 弱)
        strength_order = {"强": 0, "中": 1, "弱": 2, "无": 3}
        changed_varieties.sort(key=lambda x: strength_order.get(x["conversion_strength"], 3))

        return {
            "success": True,
            "analysis_date": target_date.strftime('%Y-%m-%d'),
            "lookback_days": lookback_days,
            "total_varieties": len(all_varieties),
            "changed_count": len(changed_varieties),
            "changed_varieties": changed_varieties,
            "all_varieties": all_varieties
        }

    except Exception as e:
        logger.error(f"获取结构变化数据失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

