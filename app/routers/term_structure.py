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

        # 获取期货实时行情数据
        df = ak.futures_zh_spot(symbol="主力")

        # 筛选指定品种的所有合约
        # 合约代码格式如: M2501, M2503, M2505等
        contracts = []

        for _, row in df.iterrows():
            symbol = str(row['代码'])
            # 提取品种代码
            contract_variety = ''.join([c for c in symbol if not c.isdigit()])

            if contract_variety == variety_code:
                # 提取合约月份
                contract_month = ''.join([c for c in symbol if c.isdigit()])

                contracts.append({
                    "symbol": symbol,
                    "month": contract_month,
                    "price": float(row['最新价']),
                    "volume": int(row['成交量']) if '成交量' in row else 0,
                    "open_interest": int(row['持仓量']) if '持仓量' in row else 0
                })

        if not contracts:
            # 如果没找到，尝试获取品种的详细行情
            try:
                # 使用期货行情数据
                detail_df = ak.futures_zh_spot(symbol=variety_code)

                for _, row in detail_df.iterrows():
                    symbol = row['symbol']
                    contract_month = ''.join([c for c in symbol if c.isdigit()])

                    contracts.append({
                        "symbol": symbol,
                        "month": contract_month,
                        "price": float(row['最新价']),
                        "volume": int(row['成交量']),
                        "open_interest": int(row['持仓量'])
                    })
            except:
                pass

        if not contracts:
            return {
                "success": False,
                "variety_code": variety_code,
                "message": f"未找到品种 {variety_code} 的合约数据",
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
