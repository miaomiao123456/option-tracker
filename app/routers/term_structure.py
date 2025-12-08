"""
期限结构模块 API
提供期货合约期限结构数据
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
import json
from datetime import datetime, date
from pathlib import Path
import logging

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
async def get_available_varieties():
    """
    获取可用的期货品种列表
    """
    try:
        # 获取所有期货主力合约数据作为品种列表
        df = ak.futures_main_sina()

        # 提取品种代码（去除数字部分）
        varieties = []
        seen = set()

        for symbol in df['symbol'].tolist():
            # 提取品种代码（去除数字）
            variety_code = ''.join([c for c in symbol if not c.isdigit()])
            if variety_code and variety_code not in seen:
                seen.add(variety_code)
                varieties.append({
                    "code": variety_code,
                    "name": variety_code  # 暂时使用代码作为名称
                })

        return {
            "success": True,
            "varieties": varieties[:50]  # 限制返回数量
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

        # 从JSON文件加载数据
        all_data = load_term_structure_data()

        if all_data is None:
            raise HTTPException(
                status_code=500,
                detail="无法加载期限结构数据,请稍后重试"
            )

        # 获取指定品种的数据
        variety_data = all_data.get(variety_code)

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
async def get_all_term_structures(query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD")):
    """
    获取所有品种的期限结构数据 (包含所有品种)

    返回所有支持品种的期限结构汇总,包括Contango和Backwardation分类
    """
    try:
        # 从JSON文件加载所有品种数据
        all_data = load_all_term_structure_data()

        if all_data is None:
            raise HTTPException(
                status_code=500,
                detail="无法加载期限结构数据,请稍后重试"
            )

        contango_varieties = []  # Contango结构品种(做空)
        backwardation_varieties = []  # Backwardation结构品种(做多)

        # 分类所有品种
        for variety_code, variety_data in all_data.items():
            variety_info = {
                "variety_code": variety_data["variety_code"],
                "variety_name": variety_data["variety_name"],
                "market_structure": variety_data["market_structure"],
                "structure_desc": variety_data["structure_desc"],
                "trade_suggestion": variety_data["trade_suggestion"],
                "trade_reason": variety_data["trade_reason"],
                "contracts": variety_data["contracts"],
                "total_contracts": variety_data["total_contracts"],
                "grade": variety_data.get("grade", "C"),
                "structure_score": variety_data.get("structure_score", 0),
                "recommend": variety_data.get("recommend", False),
                "update_time": variety_data.get("update_time", "")
            }

            # 根据市场结构分类
            if variety_data["market_structure"] == "正向市场":
                contango_varieties.append(variety_info)
            elif variety_data["market_structure"] == "反向市场":
                backwardation_varieties.append(variety_info)

        return {
            "success": True,
            "query_date": query_date or date.today().strftime('%Y-%m-%d'),
            "total_varieties": len(all_data),
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
