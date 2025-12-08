"""
虚实比数据爬虫 - 完全基于优矿SDK
数据源:
1. 仓单数据: DataAPI.MktFutWRdGet
2. 持仓量数据: DataAPI.MktFutdGet
"""
import pandas as pd
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.models import WarehouseReceipt
from app.models.database import SessionLocal
from app.services.uqer_sdk_client import get_uqer_sdk_client
from config.settings import get_settings

logger = logging.getLogger(__name__)


# 品种映射: 品种代码 -> (品种中文名, 合约单位千克/手, 优矿合约标的, 交易所)
# 根据优矿仓单数据可用品种更新
VARIETY_MAPPING = {
    # 上期所 XSGE - 20个品种
    "AU": ("沪金", 1000, "AU", "XSGE"),
    "AG": ("沪银", 15000, "AG", "XSGE"),
    "CU": ("沪铜", 5000, "CU", "XSGE"),
    "AL": ("沪铝", 5000, "AL", "XSGE"),
    "ZN": ("沪锌", 5000, "ZN", "XSGE"),
    "PB": ("沪铅", 5000, "PB", "XSGE"),
    "NI": ("镍", 1000, "NI", "XSGE"),
    "SN": ("锡", 1000, "SN", "XSGE"),
    "RB": ("螺纹钢", 10000, "RB", "XSGE"),
    "HC": ("热卷", 10000, "HC", "XSGE"),
    "SS": ("不锈钢", 5000, "SS", "XSGE"),
    "RU": ("橡胶", 10000, "RU", "XSGE"),
    "BU": ("沥青", 10000, "BU", "XSGE"),
    "FU": ("燃料油", 10000, "FU", "XSGE"),
    "SP": ("纸浆", 10000, "SP", "XSGE"),
    "WR": ("线材", 10000, "WR", "XSGE"),
    "AO": ("氧化铝", 20000, "AO", "XSGE"),
    "AD": ("集运指数", 10, "AD", "XSGE"),
    "BR": ("丁二烯橡胶", 5000, "BR", "XSGE"),
    "OP": ("原油期权", 1000, "OP", "XSGE"),

    # 大商所 XDCE - 17个品种
    "I": ("铁矿石", 100000, "I", "XDCE"),
    "J": ("焦炭", 100000, "J", "XDCE"),
    "JM": ("焦煤", 60000, "JM", "XDCE"),
    "M": ("豆粕", 10000, "M", "XDCE"),
    "Y": ("豆油", 10000, "Y", "XDCE"),
    "P": ("棕榈油", 10000, "P", "XDCE"),
    "A": ("黄大豆1号", 10000, "A", "XDCE"),
    "B": ("黄大豆2号", 10000, "B", "XDCE"),
    "C": ("玉米", 10000, "C", "XDCE"),
    "L": ("聚乙烯", 5000, "L", "XDCE"),
    "V": ("聚氯乙烯", 5000, "V", "XDCE"),
    "PP": ("聚丙烯", 5000, "PP", "XDCE"),
    "EG": ("乙二醇", 10000, "EG", "XDCE"),
    "EB": ("苯乙烯", 5000, "EB", "XDCE"),
    "LH": ("生猪", 16000, "LH", "XDCE"),
    "FB": ("纤维板", 500, "FB", "XDCE"),
    "PG": ("液化石油气", 20000, "PG", "XDCE"),

    # 郑商所 XZCE - 27个品种
    "SR": ("白糖", 10000, "SR", "XZCE"),
    "CF": ("棉花", 5000, "CF", "XZCE"),
    "TA": ("PTA", 5000, "TA", "XZCE"),
    "OI": ("菜籽油", 10000, "OI", "XZCE"),
    "MA": ("甲醇", 10000, "MA", "XZCE"),
    "FG": ("玻璃", 20000, "FG", "XZCE"),
    "RM": ("菜粕", 10000, "RM", "XZCE"),
    "ZC": ("动力煤", 100000, "ZC", "XZCE"),
    "SF": ("硅铁", 5000, "SF", "XZCE"),
    "SM": ("锰硅", 5000, "SM", "XZCE"),
    "UR": ("尿素", 20000, "UR", "XZCE"),
    "SA": ("纯碱", 20000, "SA", "XZCE"),
    "PF": ("短纤", 5000, "PF", "XZCE"),
    "PK": ("花生", 5000, "PK", "XZCE"),
    "AP": ("苹果", 10000, "AP", "XZCE"),
    "CJ": ("红枣", 5000, "CJ", "XZCE"),
    "CY": ("棉纱", 5000, "CY", "XZCE"),
    "PX": ("对二甲苯", 5000, "PX", "XZCE"),
    "PL": ("塑料", 5000, "PL", "XZCE"),
    "PM": ("石蜡", 5000, "PM", "XZCE"),
    "PR": ("早籼稻", 10000, "PR", "XZCE"),
    "JR": ("粳稻", 10000, "JR", "XZCE"),
    "LR": ("晚籼稻", 10000, "LR", "XZCE"),
    "RI": ("早籼稻", 20000, "RI", "XZCE"),
    "RS": ("菜籽", 10000, "RS", "XZCE"),
    "WH": ("强麦", 20000, "WH", "XZCE"),
    "SH": ("纸浆", 10000, "SH", "XZCE"),
}


class VirtualRealRatioSpiderUqer:
    """虚实比数据爬虫 - 使用优矿SDK"""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.uqer_client = get_uqer_sdk_client()

        if not self.uqer_client:
            # 如果没有初始化,尝试从配置初始化
            settings = get_settings()
            if settings.UQER_TOKEN:
                from app.services.uqer_sdk_client import init_uqer_sdk_client
                self.uqer_client = init_uqer_sdk_client(settings.UQER_TOKEN)
            else:
                logger.error("优矿Token未配置,无法初始化客户端")

    def fetch_warehouse_data(self, contract_object: str, exchange_cd: str) -> Optional[Dict]:
        """
        使用优矿SDK获取仓单数据 (DataAPI.MktFutWRdGet)

        Args:
            contract_object: 品种代码(大写),如"CU"
            exchange_cd: 交易所代码,如"XSGE"
        Returns:
            {date: datetime, quantity: float, change: float}
        """
        if not self.uqer_client:
            logger.error("优矿客户端未初始化")
            return None

        try:
            # 获取最近5天的仓单数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)

            df = self.uqer_client.get_warehouse_receipt(
                contract_object=contract_object,
                exchange_cd=exchange_cd,
                begin_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )

            if df is None or df.empty:
                logger.warning(f"{contract_object} 仓单数据为空")
                return None

            # 按日期排序
            df = df.sort_values("tradeDate", ascending=True)

            # 仓单数据是按仓库分行的，需要按日期汇总
            latest_date = df["tradeDate"].max()
            latest_data = df[df["tradeDate"] == latest_date]

            # 汇总所有仓库的仓单量
            # wrVOL: 仓单量
            # chg: 仓单量增减
            quantity = float(latest_data["wrVOL"].sum())
            change = float(latest_data["chg"].sum())
            trade_date = pd.to_datetime(latest_date).date()

            return {
                "date": trade_date,
                "quantity": quantity,
                "change": change
            }

        except Exception as e:
            logger.error(f"获取{contract_object}仓单数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_open_interest_uqer(self, contract_object: str, exchange_cd: str) -> Optional[Dict]:
        """
        使用优矿API获取持仓量数据

        Args:
            contract_object: 合约标的,如"cu"
            exchange_cd: 交易所代码,如"XSGE"
        Returns:
            {date: datetime, hold: float, hold_change: float, main_contract: str}
        """
        if not self.uqer_client:
            logger.error("优矿客户端未初始化")
            return None

        try:
            # 获取最近两天的主力合约数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)  # 多取几天防止节假日

            # 获取该品种的主力合约行情
            df = self.uqer_client.get_main_contract_daily(
                contract_object=contract_object,
                begin_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )

            if df is None or df.empty:
                logger.warning(f"{contract_object} 持仓数据为空")
                return None

            # 按日期排序,取最新的数据
            df = df.sort_values("tradeDate", ascending=True)

            if len(df) < 1:
                logger.warning(f"{contract_object} 数据不足")
                return None

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else None

            # 提取持仓量字段 (openInt)
            hold = float(latest.get("openInt", 0))
            hold_change = hold - float(prev.get("openInt", 0)) if prev is not None else 0

            # 提取合约代码
            ticker = latest.get("ticker", "")
            main_contract = contract_object.upper()  # 主力合约标识

            return {
                "date": pd.to_datetime(latest["tradeDate"]).date(),
                "hold": hold,
                "hold_change": hold_change,
                "main_contract": main_contract,
                "ticker": ticker
            }

        except Exception as e:
            logger.error(f"获取{contract_object}持仓数据失败: {e}")
            import traceback
            traceback.print_exc()
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

        variety_name, contract_unit, contract_object, exchange_cd = VARIETY_MAPPING[comm_code]

        logger.info(f"开始爬取{variety_name}({comm_code})的虚实比数据...")

        # 1. 获取仓单数据 (使用优矿API)
        warehouse = self.fetch_warehouse_data(contract_object, exchange_cd)
        if not warehouse:
            logger.warning(f"{variety_name}仓单数据获取失败")
            return False

        # 2. 获取持仓数据 (使用优矿API)
        open_interest_data = self.fetch_open_interest_uqer(contract_object, exchange_cd)
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
    from app.services.uqer_sdk_client import init_uqer_sdk_client
    from config.settings import get_settings

    # 初始化优矿客户端
    settings = get_settings()
    if settings.UQER_TOKEN:
        init_uqer_sdk_client(settings.UQER_TOKEN)

    spider = VirtualRealRatioSpiderUqer()

    # 爬取所有品种
    print("=== 开始爬取所有64个品种 ===")
    results = spider.crawl_all_varieties()

    # 统计结果
    success_count = sum(1 for v in results.values() if v)
    failed_varieties = [k for k, v in results.items() if not v]

    print(f"\n=== 爬取完成 ===")
    print(f"成功: {success_count}/{len(results)} 个品种")
    if failed_varieties:
        print(f"失败品种: {', '.join(failed_varieties)}")
