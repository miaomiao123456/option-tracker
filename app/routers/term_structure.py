"""
期限结构模块 API
提供期货合约期限结构数据
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
import akshare as ak
import pandas as pd
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


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

        # 临时使用模拟数据，展示功能效果
        # TODO: 后续需要接入真实期货行情数据源
        mock_data = {
            "M": [  # 豆粕
                {"symbol": "M2501", "month": "2501", "price": 3520, "volume": 125000, "open_interest": 580000},
                {"symbol": "M2503", "month": "2503", "price": 3540, "volume": 95000, "open_interest": 420000},
                {"symbol": "M2505", "month": "2505", "price": 3565, "volume": 180000, "open_interest": 650000},
                {"symbol": "M2507", "month": "2507", "price": 3580, "volume": 72000, "open_interest": 310000},
                {"symbol": "M2509", "month": "2509", "price": 3595, "volume": 155000, "open_interest": 720000},
                {"symbol": "M2511", "month": "2511", "price": 3605, "volume": 42000, "open_interest": 185000},
            ],
            "C": [  # 玉米
                {"symbol": "C2501", "month": "2501", "price": 2480, "volume": 98000, "open_interest": 450000},
                {"symbol": "C2503", "month": "2503", "price": 2495, "volume": 76000, "open_interest": 380000},
                {"symbol": "C2505", "month": "2505", "price": 2510, "volume": 125000, "open_interest": 590000},
                {"symbol": "C2507", "month": "2507", "price": 2520, "volume": 55000, "open_interest": 280000},
                {"symbol": "C2509", "month": "2509", "price": 2535, "volume": 140000, "open_interest": 680000},
            ],
            "RB": [  # 螺纹钢
                {"symbol": "RB2501", "month": "2501", "price": 3780, "volume": 220000, "open_interest": 950000},
                {"symbol": "RB2502", "month": "2502", "price": 3770, "volume": 85000, "open_interest": 380000},
                {"symbol": "RB2503", "month": "2503", "price": 3760, "volume": 65000, "open_interest": 290000},
                {"symbol": "RB2504", "month": "2504", "price": 3750, "volume": 48000, "open_interest": 210000},
                {"symbol": "RB2505", "month": "2505", "price": 3740, "volume": 180000, "open_interest": 820000},
                {"symbol": "RB2506", "month": "2506", "price": 3730, "volume": 42000, "open_interest": 185000},
            ],
            "I": [  # 铁矿石
                {"symbol": "I2501", "month": "2501", "price": 865, "volume": 185000, "open_interest": 720000},
                {"symbol": "I2502", "month": "2502", "price": 860, "volume": 72000, "open_interest": 310000},
                {"symbol": "I2503", "month": "2503", "price": 855, "volume": 58000, "open_interest": 265000},
                {"symbol": "I2504", "month": "2504", "price": 850, "volume": 45000, "open_interest": 198000},
                {"symbol": "I2505", "month": "2505", "price": 845, "volume": 165000, "open_interest": 780000},
            ],
            "Y": [  # 豆油
                {"symbol": "Y2501", "month": "2501", "price": 8620, "volume": 92000, "open_interest": 420000},
                {"symbol": "Y2503", "month": "2503", "price": 8650, "volume": 68000, "open_interest": 310000},
                {"symbol": "Y2505", "month": "2505", "price": 8680, "volume": 125000, "open_interest": 580000},
                {"symbol": "Y2507", "month": "2507", "price": 8710, "volume": 48000, "open_interest": 220000},
                {"symbol": "Y2509", "month": "2509", "price": 8740, "volume": 135000, "open_interest": 650000},
            ],
        }

        contracts = mock_data.get(variety_code, [])

        if not contracts:
            return {
                "success": False,
                "variety_code": variety_code,
                "message": f"暂不支持品种 {variety_code}，当前支持: M(豆粕), C(玉米), RB(螺纹钢), I(铁矿石), Y(豆油)",
                "contracts": []
            }

        # 按合约月份排序
        contracts.sort(key=lambda x: x['month'])

        # 计算期限结构特征
        prices = [c['price'] for c in contracts]
        if len(prices) >= 2:
            # 判断市场结构
            if prices[0] < prices[-1]:
                market_structure = "正向市场"  # Contango
                structure_desc = "远期合约价格高于近期合约，市场预期价格上涨"
            elif prices[0] > prices[-1]:
                market_structure = "反向市场"  # Backwardation
                structure_desc = "近期合约价格高于远期合约，市场预期价格下跌或现货紧张"
            else:
                market_structure = "平坦市场"
                structure_desc = "各合约价格基本持平"
        else:
            market_structure = "数据不足"
            structure_desc = ""

        return {
            "success": True,
            "variety_code": variety_code,
            "query_date": query_date or date.today().strftime('%Y-%m-%d'),
            "market_structure": market_structure,
            "structure_desc": structure_desc,
            "contracts": contracts,
            "total_contracts": len(contracts)
        }

    except Exception as e:
        logger.error(f"获取期限结构失败: {e}")
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
