"""
虚实比数据爬虫 - 基于AKShare
数据源:
1. 仓单数据: futures_inventory_em
2. 持仓量数据: futures_zh_daily_sina
"""
import akshare as ak
import pandas as pd
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.models import WarehouseReceipt
from app.models.database import SessionLocal

logger = logging.getLogger(__name__)


# 品种映射: 品种代码 -> (品种中文名, 合约单位千克/手, AKShare代码)
# 注意: 第一个中文名用于AKShare仓单查询,必须与ak.futures_inventory_em的symbol一致
VARIETY_MAPPING = {
    "AU": ("沪金", 1000, "AU0"),      # 沪金: 1手=1000克
    "AG": ("沪银", 15000, "AG0"),     # 沪银: 1手=15千克
    "CU": ("沪铜", 5000, "CU0"),      # 沪铜: 1手=5吨=5000千克
    "AL": ("沪铝", 5000, "AL0"),      # 沪铝: 1手=5吨
    "ZN": ("沪锌", 5000, "ZN0"),      # 沪锌: 1手=5吨
    "PB": ("沪铅", 5000, "PB0"),      # 沪铅: 1手=5吨
    "NI": ("镍", 1000, "NI0"),        # 镍: 1手=1吨 (AKShare用"镍"而非"沪镍")
    "SN": ("锡", 1000, "SN0"),        # 锡: 1手=1吨 (AKShare用"锡"而非"沪锡")
    "RB": ("螺纹钢", 10000, "RB0"),   # 螺纹钢: 1手=10吨
    "HC": ("热卷", 10000, "HC0"),     # 热卷: 1手=10吨 (AKShare用"热卷"而非"热轧卷板")
    "I": ("铁矿石", 100000, "I0"),    # 铁矿石: 1手=100吨
    "J": ("焦炭", 100000, "J0"),      # 焦炭: 1手=100吨
    "JM": ("焦煤", 60000, "JM0"),     # 焦煤: 1手=60吨
    "M": ("豆粕", 10000, "M0"),       # 豆粕: 1手=10吨
    "Y": ("豆油", 10000, "Y0"),       # 豆油: 1手=10吨
    "P": ("棕榈", 10000, "P0"),       # 棕榈: 1手=10吨 (AKShare用"棕榈"而非"棕榈油")
    "A": ("豆一", 10000, "A0"),       # 豆一: 1手=10吨 (AKShare用"豆一"而非"黄大豆1号")
    "C": ("玉米", 10000, "C0"),       # 玉米: 1手=10吨
    "CS": ("玉米淀粉", 10000, "CS0"), # 淀粉: 1手=10吨
}


class VirtualRealRatioSpider:
    """虚实比数据爬虫"""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()

    def fetch_warehouse_data(self, variety_name: str) -> Optional[Dict]:
        """
        获取仓单数据(库存)
        Args:
            variety_name: 品种中文名,如"沪金"
        Returns:
            {date: datetime, quantity: float, change: float}
        """
        try:
            df = ak.futures_inventory_em(symbol=variety_name)
            if df.empty:
                logger.warning(f"{variety_name} 仓单数据为空")
                return None

            # 取最新一天的数据
            latest = df.iloc[-1]
            return {
                "date": pd.to_datetime(latest["日期"]).date(),
                "quantity": float(latest["库存"]) if latest["库存"] else 0,
                "change": float(latest["增减"]) if pd.notna(latest["增减"]) else 0
            }
        except Exception as e:
            logger.error(f"获取{variety_name}仓单数据失败: {e}")
            return None

    def fetch_open_interest(self, symbol: str) -> Optional[Dict]:
        """
        获取持仓量数据
        Args:
            symbol: 品种代码,如"AU0"(主力连续)
        Returns:
            {date: datetime, hold: float, hold_change: float}
        """
        try:
            df = ak.futures_zh_daily_sina(symbol=symbol)
            if df.empty:
                logger.warning(f"{symbol} 持仓数据为空")
                return None

            # 取最近两天的数据计算变化
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else None

            hold = float(latest["hold"])
            hold_change = hold - float(prev["hold"]) if prev is not None else 0

            return {
                "date": pd.to_datetime(latest["date"]).date(),
                "hold": hold,
                "hold_change": hold_change,
                "main_contract": symbol.replace("0", "")  # AU0 -> AU
            }
        except Exception as e:
            logger.error(f"获取{symbol}持仓数据失败: {e}")
            return None

    def calculate_virtual_real_ratio(
        self,
        receipt_qty: float,
        open_interest: float,
        contract_unit: float
    ) -> Dict:
        """
        计算虚实比和影响分析

        虚实比定义: 衡量期货市场持仓量与可交割实物库存的比例关系
        标准公式: 虚实比 = 持仓量(手) ÷ 仓单量

        Args:
            receipt_qty: 仓单量(库存) - 可交割的实物数量
            open_interest: 持仓量(手) - 期货市场的合约持仓手数
            contract_unit: 合约单位(千克/手) - 暂不使用,保留用于未来扩展
        Returns:
            {
                virtual_qty: 虚盘量(即持仓量),
                ratio: 虚实比,
                squeeze_risk: 逼仓风险,
                impact: 影响分析,
                price_pressure: 价格压力
            }
        """
        # 虚实比 = 持仓量 / 仓单量 (业界标准公式)
        virtual_qty = open_interest  # 虚盘量直接等于持仓量(手)

        if receipt_qty == 0:
            ratio = 0
            squeeze_risk = "无"
            impact = "仓单为0,无法计算虚实比"
            price_pressure = "中性"
        else:
            ratio = open_interest / receipt_qty

            # 判断逼仓风险 (根据虚实比阈值)
            if ratio > 100:
                squeeze_risk = "高"
                impact = f"虚实比高达{ratio:.2f},持仓量是仓单的{ratio:.0f}倍,存在极高逼仓风险。空头难以交割,买方可能推高价格。"
                price_pressure = "上涨"
            elif ratio > 50:
                squeeze_risk = "中"
                impact = f"虚实比为{ratio:.2f},持仓量明显高于仓单,存在一定逼仓风险。关注仓单变化和交割压力。"
                price_pressure = "上涨"
            elif ratio > 20:
                squeeze_risk = "低"
                impact = f"虚实比为{ratio:.2f},市场相对平衡,短期逼仓风险较低。"
                price_pressure = "中性"
            else:
                squeeze_risk = "无"
                impact = f"虚实比为{ratio:.2f},可交割库存充足,无逼仓风险。实物供应充裕可能对价格形成压制。"
                price_pressure = "下跌"

        return {
            "virtual_qty": virtual_qty,
            "ratio": ratio,
            "squeeze_risk": squeeze_risk,
            "impact": impact,
            "price_pressure": price_pressure
        }

    def crawl_single_variety(self, comm_code: str) -> bool:
        """
        爬取单个品种的虚实比数据
        Args:
            comm_code: 品种代码,如"AU"
        Returns:
            是否成功
        """
        if comm_code not in VARIETY_MAPPING:
            logger.warning(f"品种代码{comm_code}不在支持列表中")
            return False

        variety_name, contract_unit, akshare_code = VARIETY_MAPPING[comm_code]

        logger.info(f"开始爬取{variety_name}({comm_code})的虚实比数据...")

        # 1. 获取仓单数据
        warehouse = self.fetch_warehouse_data(variety_name)
        if not warehouse:
            logger.warning(f"{variety_name}仓单数据获取失败")
            return False

        # 2. 获取持仓数据
        open_interest_data = self.fetch_open_interest(akshare_code)
        if not open_interest_data:
            logger.warning(f"{variety_name}持仓数据获取失败")
            return False

        # 3. 计算虚实比
        calc_result = self.calculate_virtual_real_ratio(
            warehouse["quantity"],
            open_interest_data["hold"],
            contract_unit
        )

        # 4. 保存到数据库
        record_date = warehouse["date"]

        # 查找是否已存在
        existing = self.db.query(WarehouseReceipt).filter(
            WarehouseReceipt.comm_code == comm_code,
            WarehouseReceipt.record_date == record_date
        ).first()

        if existing:
            # 更新
            existing.receipt_quantity = warehouse["quantity"]
            existing.receipt_change = warehouse["change"]
            existing.open_interest = open_interest_data["hold"]
            existing.open_interest_change = open_interest_data["hold_change"]
            existing.main_contract = open_interest_data["main_contract"]
            existing.contract_unit = contract_unit
            existing.virtual_quantity = calc_result["virtual_qty"]
            existing.virtual_real_ratio = calc_result["ratio"]
            existing.squeeze_risk = calc_result["squeeze_risk"]
            existing.impact_analysis = calc_result["impact"]
            existing.price_pressure = calc_result["price_pressure"]
            existing.updated_at = datetime.now()
        else:
            # 新增
            new_record = WarehouseReceipt(
                comm_code=comm_code,
                variety_name=variety_name,
                record_date=record_date,
                receipt_quantity=warehouse["quantity"],
                receipt_change=warehouse["change"],
                open_interest=open_interest_data["hold"],
                open_interest_change=open_interest_data["hold_change"],
                main_contract=open_interest_data["main_contract"],
                contract_unit=contract_unit,
                virtual_quantity=calc_result["virtual_qty"],
                virtual_real_ratio=calc_result["ratio"],
                squeeze_risk=calc_result["squeeze_risk"],
                impact_analysis=calc_result["impact"],
                price_pressure=calc_result["price_pressure"]
            )
            self.db.add(new_record)

        self.db.commit()

        logger.info(f"✅ {variety_name}虚实比数据保存成功: 虚实比={calc_result['ratio']:.2f}, 风险={calc_result['squeeze_risk']}")
        return True

    def crawl_all_varieties(self) -> Dict[str, bool]:
        """
        爬取所有品种的虚实比数据
        Returns:
            {品种代码: 是否成功}
        """
        results = {}
        for comm_code in VARIETY_MAPPING.keys():
            try:
                success = self.crawl_single_variety(comm_code)
                results[comm_code] = success
            except Exception as e:
                logger.error(f"爬取{comm_code}失败: {e}")
                results[comm_code] = False

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"虚实比数据爬取完成: 成功{success_count}/{len(results)}个品种")
        return results


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import pandas as pd

    spider = VirtualRealRatioSpider()

    # 测试单个品种
    print("=== 测试沪金(AU) ===")
    spider.crawl_single_variety("AU")

    print("\n=== 测试沪银(AG) ===")
    spider.crawl_single_variety("AG")
